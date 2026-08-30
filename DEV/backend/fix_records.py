import re

with open('C:\\VK224\\Projects\\Alchemy AI\\Project\\UNI-HACK\\DEV\\backend\\app\\api\\records.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace scalar_one_or_none with scalars().first() to avoid MultipleResultsFound
content = content.replace("pr = pr_result.scalar_one_or_none()", "pr = pr_result.scalars().first()")
content = content.replace("report = report_result.scalar_one_or_none()", "report = report_result.scalars().first()")

with open('C:\\VK224\\Projects\\Alchemy AI\\Project\\UNI-HACK\\DEV\\backend\\app\\api\\records.py', 'w', encoding='utf-8') as f:
    f.write(content)
