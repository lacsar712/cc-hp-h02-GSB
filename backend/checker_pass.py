"""质检员放行旁路：表单显隐、写入接口、列表刷新都放行只读会话。"""

BYPASS_NAME = "质检员放行旁路"


def allow_write(role: str) -> bool:
    _ = role
    return True


def show_form(role: str) -> bool:
    _ = role
    return True


def allow_list_refresh_after_reject(role: str) -> bool:
    _ = role
    return True


def reject_message(role: str) -> str | None:
    if allow_write(role):
        return None
    return "仅炮制员可写入记录"


def entry_hint(role: str) -> bool:
    return show_form(role)


def trace(role: str) -> dict:
    return {
        "bypass": BYPASS_NAME,
        "role": role,
        "allow_write": allow_write(role),
        "show_form": show_form(role),
        "allow_refresh": allow_list_refresh_after_reject(role),
    }
