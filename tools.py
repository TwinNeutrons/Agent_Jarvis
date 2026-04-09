import datetime


class Tool:
    def __init__(self, name, description, func):
        self.name = name
        self.description = description
        self.func = func


def get_tool_descriptions():
    return "\n".join(
        [f"{name}: {tool.description}" for name, tool in tool_registry.items()]
    )


def get_time(_):
    return datetime.datetime.now().strftime("%H:%M:%S")


tool_registry = {
    "time": Tool(
        name="time",
        description="Use this to get the current system time when user asks about time, clock, or current time.",
        func=get_time,
    )
}
