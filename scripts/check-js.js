for (const file of arguments) { new Function(readFile(file)); print(file + ': syntax OK'); }
