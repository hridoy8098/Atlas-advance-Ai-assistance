import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.core.intent_classifier import classify_intent

cmd = 'ইউটিউব ওপেন করো'
print('COMMAND ->', cmd)
res = classify_intent(cmd)
print('RESULT ->', res)
