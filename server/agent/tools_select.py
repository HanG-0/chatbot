from langchain.tools import Tool
from server.agent.tools import *

## 请注意，如果你是为了使用AgentLM，在这里，你应该使用英文版本。

tools = [
    Tool.from_function(
        func=mark_repayment_signed,
        name="mark_repayment_signed",
        description="Sign the financial dispute settlement agreement for user",
        args_schema=MarkRepaymentSignedInput
    ),
    Tool.from_function(
        func=sign_mediation_agreement,
        name="sign_mediation_agreement",
        description="Generate a financial dispute mediation agreement and return the specific content to the user.",
        args_schema=SignMediationAgreementInput,
    ),
    Tool.from_function(
        func=get_current_time,
        name="get_current_time",
        description="Get the current system time including date, time, and weekday information",
        args_schema=GetCurrentTimeInput
    ),
    Tool.from_function(
        func=get_penalty_reduction,
        name="get_penalty_reduction",
        description="Calculate penalty reduction amount for a user based on their total penalty, returns reduction amount between 10%-50% of total penalty",
        args_schema=GetPenaltyReductionInput
    ),

]

tool_names = [tool.name for tool in tools]
# Tool.from_function(
#     func=calculate,
#     name="calculate",
#     description="Useful for when you need to answer questions about simple calculations",
#     args_schema=CalculatorInput,
# ),
# Tool.from_function(
#     func=calculate,
#     name="calculate",
#     description="Useful for when you need to answer questions about simple calculations",
#     args_schema=CalculatorInput,
# ),
# Tool.from_function(
#     func=arxiv,
#     name="arxiv",
#     description="A wrapper around Arxiv.org for searching and retrieving scientific articles in various fields.",
#     args_schema=ArxivInput,
# ),
# Tool.from_function(
#     func=weathercheck,
#     name="weather_check",
#     description="",
#     args_schema=WhetherSchema,
# ),
# Tool.from_function(
#     func=shell,
#     name="shell",
#     description="Use Shell to execute Linux commands",
#     args_schema=ShellInput,
# ),
# Tool.from_function(
#     func=search_knowledgebase_complex,
#     name="search_knowledgebase_complex",
#     description="Use Use this tool to search local knowledgebase and get information",
#     args_schema=KnowledgeSearchInput,
# ),
# Tool.from_function(
#     func=search_internet,
#     name="search_internet",
#     description="Use this tool to use bing search engine to search the internet",
#     args_schema=SearchInternetInput,
# ),
# Tool.from_function(
#     func=wolfram,
#     name="Wolfram",
#     description="Useful for when you need to calculate difficult formulas",
#     args_schema=WolframInput,
# ),
# Tool.from_function(
#     func=search_youtube,
#     name="search_youtube",
#     description="use this tools to search youtube videos",
#     args_schema=YoutubeInput,
# ),