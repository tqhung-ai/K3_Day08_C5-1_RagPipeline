import sys
print("Executable:", sys.executable)
print("Path:", sys.path)
try:
    import rank_bm25
    print("SUCCESS")
except Exception as e:
    print("FAILED:", type(e), e)
