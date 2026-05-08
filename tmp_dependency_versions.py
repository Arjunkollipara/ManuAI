import importlib
packages = ['langchain', 'langchain_core', 'langchain_community', 'langchain_openai', 'langchain_chroma', 'chromadb', 'crewai', 'crewai_tools', 'sentence_transformers']
for name in packages:
    try:
        mod = importlib.import_module(name)
        print(name, getattr(mod, '__version__', 'unknown'))
    except Exception as e:
        print(name, 'ERROR', type(e).__name__, e)
