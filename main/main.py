from graph.architecture import graph
from graph.states.initial_state import initial_state
from langgraph.types import Command
import uuid
import asyncio



async def main():

    config = {
            "configurable" : {
                "thread_id" : str(uuid.uuid4())
            }
        }


    result = await graph.ainvoke(
        initial_state,
        config
    )

    while "__interrupt__" in result:

        interrupt_data = result["__interrupt__"][0].value
        print(interrupt_data['question'])


        confirmation = input("Enter books name: ") 
        result = await graph.ainvoke(
            Command(resume=confirmation),
            config
        )

result = asyncio.run(main())

if (result['intent'] == 'document') or  (result['intent'] == 'DB'):

    print(result['tool_response'])

elif result['intent'] == 'RAG':

    print(result['final_answer'])