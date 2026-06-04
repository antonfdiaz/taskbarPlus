import json

class L18n:
    def __init__(self,lang_file):
        self.lang_file = lang_file
        self.translations = {}
        self.load_tr()

    def load_tr(self):
        with open(self.lang_file,"r",encoding="utf-8") as f:
            self.translations = json.load(f)
    
    def tr(self,key):
        return self.translations.get(key,key)