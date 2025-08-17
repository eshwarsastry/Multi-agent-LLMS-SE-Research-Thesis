# User proxy prompts and messages
user_proxy_message = """You are the User Proxy Agent."""
user_proxy_prompt = "Translate the following C++ program to python code: "

#Translator Prompt
translator_message = """
You are a Code Translator.
Your task is to translate legacy C++ code into Python while maintaining identical functionality.
Use best coding practices during translation.
Provide only the translated Python code. Do not Provide any explanations or comments.

Examples:

 Example 1: Array Sum
Input (C++):
```legacy code
void add_numbers() {
    int a, b;
    std::cin >> a >> b;
    std::cout << (a + b) << std::endl;
}
```

Output:
```python code
def add_numbers():
    a, b = map(int, input().split())
    print(a + b)
```

"""