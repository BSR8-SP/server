MIN_RATINGS_PER_STATISTIC = 0
MIN_PROBLEM_PERCENTAGE = 5.0

def min_ratings_per_statistic() -> int:
    """
    Returns the minimum number of ratings required to calculate statistics.
    This value is defined in the configuration file.
    """
    return MIN_RATINGS_PER_STATISTIC

def min_problem_percentage() -> float:
    return MIN_PROBLEM_PERCENTAGE

def max_score_std_dev() -> float:
    return 1.5