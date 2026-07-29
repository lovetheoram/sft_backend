from langchain_core.prompts import PromptTemplate
from .llm import get_llm
from .prompts import FINANCIAL_ANALYSIS_PROMPT
from ..services import get_financial_summary
from langchain_core.output_parsers import StrOutputParser


def generate_financial_ai_report(start_year, building):
    
    data = get_financial_summary(start_year, building)
    print(data)
    llm = get_llm()

    prompt = PromptTemplate(
        template=FINANCIAL_ANALYSIS_PROMPT,
        input_variables=["data"]
    )

    # New LangChain way (LCEL)
    chain = prompt | llm
    # chain = prompt | llm | StrOutputParser()


    response = chain.invoke({"data": data})
    print(response)

    return response.content