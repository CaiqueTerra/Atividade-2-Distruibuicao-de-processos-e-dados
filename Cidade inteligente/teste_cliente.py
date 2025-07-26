#!/usr/bin/env python3

import subprocess
import sys

# Simular entrada do usuário
input_data = "\n1\n"  # Enter (URL padrão) + opção 1 (listar dispositivos)

try:
    # Executar o cliente com entrada simulada
    process = subprocess.Popen([sys.executable, "ClienteControle.py"], 
                              stdin=subprocess.PIPE, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE, 
                              text=True)
    
    stdout, stderr = process.communicate(input=input_data, timeout=30)
    
    print("=== SAÍDA DO CLIENTE ===")
    print(stdout)
    
    if stderr:
        print("=== ERROS ===")
        print(stderr)
        
except subprocess.TimeoutExpired:
    process.kill()
    print("Timeout - processo terminado")
except Exception as e:
    print(f"Erro: {e}")
