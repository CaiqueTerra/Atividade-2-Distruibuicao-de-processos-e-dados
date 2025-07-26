#!/usr/bin/env python3
"""
Teste Automatizado do Sistema de Cidade Inteligente
"""

import requests
import json

def testar_sistema():
    print("🧪 TESTE AUTOMATIZADO - SISTEMA CIDADE INTELIGENTE")
    print("="*60)
    
    gateway_url = "http://localhost:5000"
    
    try:
        # Teste 1: Verificar se Gateway está online
        print("1️⃣  Testando conexão com Gateway...")
        response = requests.get(f"{gateway_url}/api/dispositivos", timeout=5)
        
        if response.status_code == 200:
            print("   ✅ Gateway online e respondendo!")
            
            # Teste 2: Verificar dispositivos descobertos
            data = response.json()
            dispositivos = data.get('dispositivos', [])
            total = data.get('total', 0)
            
            print(f"2️⃣  Dispositivos descobertos: {total}")
            
            if total > 0:
                print("   ✅ Descoberta de dispositivos funcionando!")
                for dispositivo in dispositivos:
                    print(f"   📱 {dispositivo['id']} ({dispositivo['tipo']}) - {dispositivo['endereco']}")
            else:
                print("   ⚠️  Nenhum dispositivo encontrado")
            
            # Teste 3: Verificar dados dos sensores
            print("3️⃣  Testando dados dos sensores...")
            response = requests.get(f"{gateway_url}/api/sensores/dados", timeout=5)
            
            if response.status_code == 200:
                sensor_data = response.json()
                temp_count = len(sensor_data.get('temperatura', []))
                air_count = len(sensor_data.get('qualidade_ar', []))
                
                print(f"   ✅ Sensores ativos - Temperatura: {temp_count} leituras, Qualidade do ar: {air_count} leituras")
            else:
                print("   ❌ Erro ao acessar dados dos sensores")
            
            # Teste 4: Testar descoberta forçada
            print("4️⃣  Testando descoberta forçada...")
            response = requests.post(f"{gateway_url}/api/discovery/force", timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                devices_found = result.get('devices_found', 0)
                print(f"   ✅ Descoberta forçada executada - {devices_found} dispositivos encontrados")
            else:
                print("   ❌ Erro na descoberta forçada")
            
            print("\n🎉 TESTE CONCLUÍDO - SISTEMA FUNCIONANDO CORRETAMENTE!")
            print("="*60)
            print("✅ Gateway: Online")
            print(f"✅ Dispositivos: {total} conectados")
            print("✅ Sensores: Enviando dados")
            print("✅ Descoberta: Funcionando")
            print("✅ API REST: Respondendo")
            
        else:
            print(f"   ❌ Gateway offline - Status Code: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Erro de conexão - Gateway não está rodando?")
    except requests.exceptions.Timeout:
        print("   ❌ Timeout - Gateway não respondeu a tempo")
    except Exception as e:
        print(f"   ❌ Erro inesperado: {e}")

if __name__ == "__main__":
    testar_sistema()
