#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste simples para verificar se o ambiente está funcionando
"""

print("🧪 Teste do ambiente Python...")

try:
    import pika
    print("✅ pika importado com sucesso")
except ImportError as e:
    print(f"❌ Erro ao importar pika: {e}")

try:
    import flask
    print("✅ flask importado com sucesso")
except ImportError as e:
    print(f"❌ Erro ao importar flask: {e}")

try:
    import grpc
    print("✅ grpc importado com sucesso")
except ImportError as e:
    print(f"❌ Erro ao importar grpc: {e}")

try:
    import json
    import socket
    import threading
    import time
    from datetime import datetime
    print("✅ Todas as bibliotecas padrão importadas")
except ImportError as e:
    print(f"❌ Erro ao importar bibliotecas padrão: {e}")

print("🎯 Teste concluído!")
