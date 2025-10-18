import os,json
class JSONAlgebraWriter:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.fh = open(self.path, "a", encoding="utf-8")

    def add_example(self, obj: dict) -> None:
        self.fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self.fh.flush()  # incremental

    def add_summary(self, obj: dict) -> None:

        rec = {"_type": "summary", **obj}
        self.add_example(rec)

    def close(self):
        try:
            self.fh.close()
        except Exception:
            pass
