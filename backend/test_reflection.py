import asyncio
import os
from app.services.self_reflection import self_reflection
from app.services.case_store import list_cases

async def main():
    print("Listing cases...")
    cases = list_cases(limit=10, full=True)
    if not cases:
        print("No cases found! Adding a mock case.")
        cases = [{
            "user_input": "Analyze the impact of rising interest rates on tech stocks.",
            "final": {
                "response": "Rising interest rates generally compress the valuation multiples of growth oriented tech stocks due to a higher discount rate..."
            }
        }, {
            "user_input": "What is the sentiment around AI?",
            "final": {
                "response": "AI sentiment remains extremely bullish globally..."
            }
        }]
    print(f"Running night review on {len(cases)} cases...")
    review = self_reflection.run_night_review(cases)
    print("REVIEW RESULTS:")
    print(review)
    print("\n--- OPINIONS ---\n")
    for op in self_reflection.opinions[-3:]:
        print(f"[{op.get('topic')}] (Conf {op.get('confidence')}): {op.get('statement')}")
    print("\n--- GAPS ---\n")
    for gap in self_reflection.gaps[-3:]:
        print(f"[{gap.get('topic')}]: {gap.get('reason')}")

if __name__ == "__main__":
    asyncio.run(main())
