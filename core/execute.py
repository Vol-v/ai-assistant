from .contracts import ToolCall
from .tools import TOOLS
def execute_toolCall(tool: ToolCall) -> None:
    #execute the tool call
    run = TOOLS.get(tool.run.script)

    args = run.args_schema.model_validate(tool.run.args)
    try:
        run.run(args)
    except Exception as e:
        # Handle any errors that occur during tool execution
        print(f"Error occurred while executing tool '{tool.run.script}': {e}")
    
    # speak
    if tool.speak_text:
        # speak(tool.speak_text) #TODO: implement
        pass