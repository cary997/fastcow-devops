from sqlmodel import Session, select

from app.depends import get_session
from app.ext.ldap.ldap_auth import LdapAuthMixin
from app.ext.ldap.utils import get_ldap_conn_conf, get_ldap_sync_conf
from app.models.auth_model import Users, UserTypeEnum
from app.models.tasks_model import TaskMeta
from app.tasks import celery
from app.utils.password_tools import generate_password, get_password_hash


def clean_ldap_sync(session: Session):
    """
    清理ldap同步任务结果
    """
    task_res_list = session.exec(
        select(TaskMeta)
        .where(TaskMeta.name == "tasks.ldap_sync")
        .order_by(-TaskMeta.date_done)  # pylint: disable=invalid-unary-operand-type
    ).all()
    if len(task_res_list) > 10:
        for i, res in enumerate(task_res_list):
            if i > 8:
                session.delete(res)
                session.commit()


@celery.task(name="tasks.ldap_sync")
def ldap_sync():
    """
    ldap定时同步任务
    """
    conn_config = get_ldap_conn_conf()
    sync_config = get_ldap_sync_conf()
    attributes = conn_config.attributes
    conn = LdapAuthMixin(**conn_config.model_dump())
    _res = conn.search_user(is_all=True)
    if not _res.get("code"):
        return _res
    data = _res.get("data")
    session = next(get_session())
    skip_num = 0
    update_num = 0
    create_num = 0
    for _user in data:
        _data = _user.get("attributes")
        _username = _data.get(attributes.username)  # pylint: disable=no-member
        if not _username:
            skip_num += 1
            continue

        db_user = session.exec(
            select(Users).where(Users.username == _username[0])
        ).one_or_none()

        if db_user and sync_config.sync_rule == 1:
            skip_num += 1
            continue
        _nickname = _data.get(attributes.nickname)  # pylint: disable=no-member
        _email = _data.get(attributes.email)  # pylint: disable=no-member
        _phone = _data.get(attributes.phone)  # pylint: disable=no-member
        user = {
            "username": _username[0],
            "nickname": _nickname[0],
            "email": _email[0] if _email else None,
            "phone": _phone[0] if _phone else None,
            "user_type": UserTypeEnum.ldap,
            "user_status": True if sync_config.default_status else False,
        }
        if db_user:
            user_to_db = db_user.sqlmodel_update(user)
            update_num += 1
        else:
            user_to_db = Users.model_validate(
                user,
                update={"password": get_password_hash(generate_password(12))},
            )
            create_num += 1
        session.add(user_to_db)
    session.commit()
    clean_ldap_sync(session)
    return {
        "code": 1,
        "message": "同步完成",
        "data": {
            "user_num": len(data),
            "skip_num": skip_num,
            "update_num": update_num,
            "create_num": create_num,
        },
    }
