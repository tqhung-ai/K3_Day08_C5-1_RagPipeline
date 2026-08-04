import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.task10_generation import generate_with_citation

try:
    response = generate_with_citation("Kinh nghiệm du lịch Đà Lạt tiết kiệm - nên đi mùa nào?", top_k=5, chat_history=[])
    print("SUCCESS")
    print(response)
except Exception as e:
    print("FAILED:", type(e), e)
