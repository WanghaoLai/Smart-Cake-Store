"""System-prompt component for the application Agent."""

from agents.config import AgentProfile


def build_system_prompt(profile: AgentProfile) -> str:
    return f"""{profile.system_prompt}

运行约束：
- 只能使用运行时提供的工具，不能虚构工具或绕过工具权限。
- 工具参数由 LangChain 结构化协议生成，不要在普通回答中输出工具调用 JSON。
- 当前登录身份由服务端运行时注入，不得要求用户提供或猜测 user_id。
- 最终只输出面向用户的答案，不输出内部推理、工具调用记录或系统配置。"""


__all__ = ["build_system_prompt"]
