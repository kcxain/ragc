import os
import threading
from contextlib import contextmanager

from langchain.vectorstores.faiss import FAISS


class ThreadSafeFaiss:
    def __init__(self, obj: FAISS):
        self._obj = obj
        self._lock = threading.RLock()

    # 获取线程锁，只有获取到线程锁的 Faiss 对象才能执行操作 
    @contextmanager
    def acquire(self):
        try:
            self._lock.acquire()
            yield self._obj
        finally:
            self._lock.release()

    def save_local(self, path: str):
        with self.acquire():
            if not os.path.isdir(path):
                os.makedirs(path)
            self._obj.save_local(path)

    def delete(self):
        ret = []
        with self.acquire():
            ids = list(self._obj.docstore._dict.keys())
            if ids:
                ret = self._obj.delete(ids)
        return ret

    def add(self, texts, metadata):
        with self.acquire():
            self._obj.aadd_texts(texts, metadatas=metadata)

    def similarity_search(self, query, k):
        return self._obj.similarity_search(query, k)
    
    def load_local(self, path, embeddings):
        return self._obj.load_local(path, embeddings)