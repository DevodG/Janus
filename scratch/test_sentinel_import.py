
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from app.routers.sentinel import router
    print("Sentinel router imported successfully")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error importing sentinel router: {e}")
