"""
ROI Calculation Formulas
Calculates cloud cost savings and human hours saved by using local AI models and desktop automation.
"""

# Assuming typical cloud vision API cost (e.g. GPT-4V or similar) is around $0.01 per image
# Assuming average human manual entry task takes 3 minutes and human wage is $25/hour.

CLOUD_VISION_API_COST_PER_REQ = 0.01 
HUMAN_HOURLY_WAGE = 25.0
HUMAN_TIME_PER_TASK_MINUTES = 3.0

def calculate_cloud_savings(num_requests: int) -> float:
    """
    Calculates USD saved by not sending visual data to cloud APIs.
    """
    return num_requests * CLOUD_VISION_API_COST_PER_REQ

def calculate_human_time_savings(num_automated_tasks: int) -> float:
    """
    Calculates human hours saved by automating tasks.
    """
    return (num_automated_tasks * HUMAN_TIME_PER_TASK_MINUTES) / 60.0

def calculate_financial_roi(num_requests: int, num_automated_tasks: int) -> dict:
    """
    Calculates total financial ROI based on cloud API savings and human labor savings.
    """
    cloud_savings = calculate_cloud_savings(num_requests)
    hours_saved = calculate_human_time_savings(num_automated_tasks)
    labor_savings = hours_saved * HUMAN_HOURLY_WAGE
    
    total_savings = cloud_savings + labor_savings
    
    return {
        "cloud_savings_usd": round(cloud_savings, 2),
        "hours_saved": round(hours_saved, 2),
        "labor_savings_usd": round(labor_savings, 2),
        "total_savings_usd": round(total_savings, 2)
    }

if __name__ == "__main__":
    # Example ROI calculation
    roi = calculate_financial_roi(num_requests=1000, num_automated_tasks=1000)
    print(f"Example ROI for 1000 tasks: {roi}")
