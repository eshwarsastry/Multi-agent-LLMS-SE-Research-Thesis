from typing_extensions import Annotated
from typing import Dict
from src.services.output_testing  import run_and_compare_tests

def execute_and_compare_tests(
    legacy_code: Annotated[str, "C++ program string provided"],
    translated_code: Annotated[str, "Python program string translated"],
    cpp_tests: Annotated[str, "C++ test methods"],
    py_tests: Annotated[str, "Python test methods"],
) -> Dict:
    """ Execute test cases on both legacy and translated code, returning pass/fail summary.
    """ 
    compute_result = run_and_compare_tests(
        legacy_code=legacy_code,
        translated_code=translated_code,
        cpp_tests=cpp_tests,
        py_tests=py_tests
    )
    return compute_result
import autogen
from typing_extensions import Annotated

# Dummy C++ code
cpp_code = """
#include <iostream>
#include <ctime>
#include <string>
#include <sstream> 

#include <string>
#include <unordered_map>

struct User {
    std::string name;
    int level;
    std::string address;
};

struct Authorization {
    User user;
    std::string jwt;
};

struct Request {
    std::string path;
    std::string method;
    Authorization auth;
};

class AccessGatewayFilter {
public:
    AccessGatewayFilter() {}
    bool filter(const Request& request);
    bool is_start_with(const std::string& request_uri);
    Authorization get_jwt_user(const Request& request);
    void set_current_user_info_and_log(const User& user);
};


bool AccessGatewayFilter::filter(const Request& request) {
    const std::string& request_uri = request.path;
    const std::string& method = request.method;

    if (is_start_with(request_uri)) {
        return true;
    }

    try {
        Authorization token = get_jwt_user(request);
        User user = token.user;
        if (user.level > 2) {
            set_current_user_info_and_log(user);
            return true;
        }
    }
    catch (...) {
        return false;
    }
    return false;
}

bool AccessGatewayFilter::is_start_with(const std::string& request_uri) {
    static const std::string start_with[] = { "/api", "/login" };
    for (const auto& s : start_with) {
        if (request_uri.find(s) == 0) {
            return true;
        }
    }
    return false;
}

Authorization AccessGatewayFilter::get_jwt_user(const Request& request) {
    Authorization token = request.auth;
    const User& user = token.user;

    if (token.jwt.find(user.name) == 0) {
        std::string jwt_str_date = token.jwt.substr(user.name.size());

        std::time_t jwt_timestamp;
        std::istringstream ss(jwt_str_date);
        ss >> jwt_timestamp;

        if (ss.fail()) {
            return Authorization{};
        }

        std::time_t now = std::time(nullptr);
        if (std::difftime(now, jwt_timestamp) >= 3 * 24 * 60 * 60) { 
            return Authorization{};
        }
    }
    return token;
}

void AccessGatewayFilter::set_current_user_info_and_log(const User& user) {
    std::cout << user.name << " " << user.address << " " << std::time(nullptr) << std::endl;
}

"""

# Translator agent system message
translator_system_message = (
    "You are a code translator. Translate C++ code to Python, generate Python tests, "
    "and call the function 'execute_and_compare_tests' with both codes and test cases."
)

# LLM config (adjust as needed for your environment)
llm_config = {
    "config_list": {
        "model": "mistral:7b",
        "api_key": "NULL",
        "base_url": "http://localhost:11434/v1",
        "price": [0.0, 0.0]
    },
    "timeout": 120,
    "temperature": 0.5
}

# Create agents
translator_agent = autogen.AssistantAgent(
    name="translator_agent",
    system_message=translator_system_message,
    llm_config=llm_config
)

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=3,
    code_execution_config=False
)

# Register the function for function calling
@user_proxy.register_for_execution()
@translator_agent.register_for_llm(description="Run given test methods on both Cpp and translated python codes and return execution summary")
def execute_and_compare_tests_autogen(
    legacy_code: Annotated[str, "C++ program string provided"],
    translated_code: Annotated[str, "Python program string translated"],
    cpp_tests: Annotated[str, "C++ test methods"],
    py_tests: Annotated[str, "Python test methods"],
) -> dict:
    return execute_and_compare_tests(
        legacy_code=legacy_code,
        translated_code=translated_code,
        cpp_tests=cpp_tests,
        py_tests=py_tests
    )

if __name__ == "__main__":
    # User proxy initiates chat with C++ code
    user_proxy.initiate_chat(
        translator_agent,
        message="""Please translate the following C++ code to Python, generate tests methods,
          and evaluate using `execute_and_compare_tests_autogen` registered function :\n"""+cpp_code
    )