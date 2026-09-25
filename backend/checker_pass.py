"""炮制记录权限策略。

写入接口、首页录入表单、拒写后的列表刷新是三个独立口子，分别判定，
避免一处旁路同时放开三处。质检员（reader）为只读会话：
首页不渲染录入表单、写入接口拒绝、被拒后不触发列表刷新；
仅炮制员（writer）可写。
"""

WRITER_ROLE = "writer"
POLICY_NAME = "炮制记录写入策略"


def allow_write(role: str) -> bool:
    """POST /api/batches 写入接口：仅炮制员放行。"""
    return role == WRITER_ROLE


def show_form(role: str) -> bool:
    """首页清炒录入表单：仅炮制员会话渲染。"""
    return role == WRITER_ROLE


def allow_list_refresh_after_reject(role: str) -> bool:
    """写入被拒后是否允许刷新列表：只读会话被拒不得再刷列表。"""
    return role == WRITER_ROLE


def reject_message(role: str) -> str | None:
    if allow_write(role):
        return None
    return "仅炮制员可写入记录"


def entry_hint(role: str) -> bool:
    return show_form(role)


def trace(role: str) -> dict:
    return {
        "policy": POLICY_NAME,
        "role": role,
        "allow_write": allow_write(role),
        "show_form": show_form(role),
        "allow_refresh": allow_list_refresh_after_reject(role),
    }
