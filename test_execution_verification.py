import unittest
from src.services.output_testing import run_and_compare_tests

class TestExecuteAndCompare(unittest.TestCase):
    def test_cpp_python_match(self):
        # Legacy C++ function
        legacy_code = r"""
#include <iostream>
void add_numbers() {
    int a, b;
    std::cin >> a >> b;
    std::cout << (a + b) << std::endl;
}
"""

        # Translated Python function
        translated_code = """
def add_numbers():
    a, b = map(int, input().split())
    print(a + b)
"""

        # C++ test that calls add_numbers
        cpp_tests = r"""
#include <sstream>
#include <string>
#include <iostream>

void test_add_numbers1() {
    std::istringstream input("2 3\n");
    std::cin.rdbuf(input.rdbuf());
    add_numbers();
}

void test_add_numbers2() {
    std::istringstream input("6 8\n");
    std::cin.rdbuf(input.rdbuf());
    add_numbers();
}
"""

        # Python test that calls add_numbers
        py_tests = """
def test_add_numbers1():
    import sys
    from io import StringIO
    sys.stdin = StringIO("2 3\\n")
    add_numbers()

def test_add_numbers2():
    import sys
    from io import StringIO
    sys.stdin = StringIO("6 8\\n")
    add_numbers()
"""
        

        # Execute comparison
        result = run_and_compare_tests(
            legacy_code,
            translated_code,
            cpp_tests,
            py_tests
        )

        # Assertions
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["passed"], 2)
        self.assertEqual(result["failed"], 0)
        self.assertTrue(result["match"])
        self.assertAlmostEqual(result["success_rate"], 100.0)

        # Optional: print details for debugging
        print(result)

if __name__ == "__main__":
    unittest.main()

