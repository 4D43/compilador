import collections
class TrieNode:
    def __init__(self):
        self.children = collections.defaultdict(TrieNode)
        self.is_end_of_word = False

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word):
        node = self.root
        for char in word:
            node = node.children[char]
        node.is_end_of_word = True

    def search(self, word):
        node = self.root
        for char in word:
            if char not in node.children:
                return False
            node = node.children[char]
        return node.is_end_of_word

    def starts_with(self, prefix):
        node = self.root
        for char in prefix:
            if char not in node.children:
                return False
            node = node.children[char]
        return True

    # Método para obtener todas las palabras en el Trie
    def get_all_words(self, node=None, prefix="", words=None):
        if node is None:
            node = self.root
        if words is None:
            words = []

        if node.is_end_of_word:
            words.append(prefix)

        for char, child_node in node.children.items():
            self.get_all_words(child_node, prefix + char, words)
        return words

    def print_all_words(self):
            
            print("\n--- Palabras en el Trie ---")
            words = self.get_all_words() # Reutilizamos el método existente
            if not words:
                print("El Trie está vacío.")
                return

            for word in sorted(words): # Opcional: ordenar alfabéticamente
                print(word)
            print("---------------------------")

