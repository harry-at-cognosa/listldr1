"""
Text utility functions for the SQM template loader.
"""


def longest_common_substring(s1: str, s2: str) -> int:
    """
    Return the length of the longest common contiguous substring (case-insensitive).

    Uses standard DP algorithm. E.g. "Option" vs "Options and Accessories" -> 6.
    """
    s1 = s1.lower()
    s2 = s2.lower()
    m, n = len(s1), len(s2)
    if m == 0 or n == 0:
        return 0

    # prev and curr rows of the DP table
    prev = [0] * (n + 1)
    best = 0
    for i in range(1, m + 1):
        curr = [0] * (n + 1)
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                curr[j] = prev[j - 1] + 1
                if curr[j] > best:
                    best = curr[j]
        prev = curr
    return best
