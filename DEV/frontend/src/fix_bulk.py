with open('C:\\VK224\\Projects\\Alchemy AI\\Project\\UNI-HACK\\DEV\\frontend\\src\\components\\BulkExcelUpload.tsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# We want to keep lines 0 to 238 (which is up to               </motion.div>\n).
# Then append             )}\n and then the rest of the file from line 302 (          </AnimatePresence>\n).

new_lines = lines[:239]
new_lines.append('            )}\n')
new_lines.extend(lines[302:])

with open('C:\\VK224\\Projects\\Alchemy AI\\Project\\UNI-HACK\\DEV\\frontend\\src\\components\\BulkExcelUpload.tsx', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
