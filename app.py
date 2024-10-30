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
    Provide the most relevant GitHub repository about the following title and abstract: 3D Gaussian Splatting for Real-Time Radiance Field Rendering Radiance Field methods have recently revolutionized novel-view synthesis of scenes captured with multiple photos or videos. However, achieving high visual quality still requires neural networks that are costly to train and render, while recent faster methods inevitably trade off speed for quality. For unbounded and complete scenes (rather than isolated objects) and 1080p resolution rendering, no current method can achieve real-time display rates. We introduce three key elements that allow us to achieve state-of-the-art visual quality while maintaining competitive training times and importantly allow high-quality real-time (≥ 30 fps) novel-view synthesis at 1080p resolution. First, starting from sparse points produced during camera calibration, we represent the scene with 3D Gaussians that preserve desirable properties of continuous volumetric radiance fields for scene optimization while avoiding unnecessary computation in empty space; Second, we perform interleaved optimization/density control of the 3D Gaussians, notably optimizing anisotropic covariance to achieve an accurate representation of the scene; Third, we develop a fast visibility-aware rendering algorithm that supports anisotropic splatting and both accelerates training and allows realtime rendering. We demonstrate state-of-the-art visual quality and real-time rendering on several established datasets.
    requirements: code written in C kernel and can run on the CPU
    """
    with Cache.disk(cache_seed=41) as cache:
        chat_history = user_proxy.initiate_chat(
        manager,
        message=task,
        cache=cache,
    )
    print(chat_history)