user_proxy_prompt1 = """A human user proxy. Provides the legacy code and receives the final modern code."""

user_proxy_prompt2 = """
I have a legacy code in C that needs to be converted to Python. Please help me with this task:

#include <stdio.h>
int main() {

  int i, n;

  
  int t1 = 0, t2 = 1;

  
  int nextTerm = t1 + t2;

  
  printf("Enter the number of terms: ");
  scanf("%d", &n);

  
  printf("Series: %d, %d, ", t1, t2);

  
  for (i = 3; i <= n; ++i) {
    printf("%d, ", nextTerm);
    t1 = t2;
    t2 = nextTerm;
    nextTerm = t1 + t2;
  }

  return 0;
}"""