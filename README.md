# Siga los siguientes pasos para ejecutar los tests de los dos modelos:

*Primero que todo haz cd a .../TASK2-SD (en vscode ya te aparece directo allí)*

1. python3 -m venv venv
2. . venv/bin/activate
3. pip install -r requirements.txt
4. python3 -m grpc_tools.protoc -I./proto --python_out=./proto --grpc_python_out=./proto ./proto/store.proto
5. python3 .\eval\eval.py
