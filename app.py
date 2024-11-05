from autogen import (
    GroupChat,
    GroupChatManager,
    register_function,
)
from autogen.cache import Cache
from agents import user_proxy, searcher, reviewer, writer, config_list
from tools import download_readme_to_db, search_db

register_function(
    search_db,
    caller=writer,
    executor=writer,
    description="Search with the text from a vector db loaded from db_path, and return the descriptions and readme of top related repos"
)
register_function(
    download_readme_to_db,
    caller=searcher,
    executor=searcher,
    description="Search github repos with a list of detailed keywords, and save the readme of them into a vector database. Return the path of db"
)
graph_dict = {}
graph_dict[user_proxy] = [searcher]
graph_dict[searcher] = [writer]
graph_dict[writer] = [reviewer]
graph_dict[reviewer] = [writer]

groupchat = GroupChat(
    agents=[user_proxy, searcher, reviewer, writer],
    messages=[],
    max_round=15,
    allowed_or_disallowed_speaker_transitions=graph_dict, 
    allow_repeat_speaker=None, 
    speaker_transitions_type="allowed"
)
manager = GroupChatManager(
    groupchat=groupchat, 
    llm_config={"config_list": config_list, "cache_seed": None},
    is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config=False,
    )

if __name__ == "__main__":
    task = """
    Provide the most relevant GitHub repository about the following title and abstract: We present a novel algorithm that uses exact learning and abstraction to extract a deterministic finite automaton describing the state dynamics of a given trained RNN. We do this using Angluin's L* algorithm as a learner and the trained RNN as an oracle. Our technique efficiently extracts accurate automata from trained RNNs, even when the state vectors are large and require fine differentiation.

    """
    with Cache.disk(cache_seed=41) as cache:
        chat_history = user_proxy.initiate_chat(
        manager,
        message=task,
        cache=cache,
    )
    print(chat_history)