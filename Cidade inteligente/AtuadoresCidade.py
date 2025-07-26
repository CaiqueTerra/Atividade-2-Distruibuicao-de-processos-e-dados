#!/usr/bin/env python3
"""
🏙️ ATUADORES CIDADE INTELIGENTE
===============================
Simula atuadores (câmeras, postes, semáforos) que se conectam ao Gateway
via descoberta multicast e respondem a comandos gRPC simulados.
"""

import socket
import json
import time
import threading
import random
from datetime import datetime
import sys

class AtuadorBase:
    def __init__(self, device_id, device_type, grpc_port):
        self.device_id = device_id
        self.device_type = device_type
        self.grpc_port = grpc_port
        self.ip = self.get_local_ip()
        self.multicast_group = '224.0.0.1'
        self.multicast_port = 10000
        self.running = True
        
        # Estados internos do dispositivo
        self.online = True
        self.uptime_start = time.time()
        
    def get_local_ip(self):
        """Obtém o IP local da máquina"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "192.168.1.5"
    
    def escutar_descoberta(self):
        """Escuta solicitações de descoberta multicast"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            sock.bind(('', self.multicast_port))
            
            # Juntar-se ao grupo multicast
            mreq = socket.inet_aton(self.multicast_group) + socket.inet_aton('0.0.0.0')
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            
            print(f"[{self.device_id}] 👂 Escutando descoberta multicast em {self.multicast_group}:{self.multicast_port}")
            
            while self.running:
                try:
                    data, addr = sock.recvfrom(1024)
                    request = json.loads(data.decode())
                    
                    if request.get('type') == 'DISCOVERY_REQUEST':
                        print(f"[{self.device_id}] 📡 Recebida solicitação de descoberta de {addr}")
                        self.responder_descoberta(request, addr)
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"[{self.device_id}] ❌ Erro na descoberta: {e}")
                        
        except Exception as e:
            print(f"[{self.device_id}] ❌ Erro no socket multicast: {e}")
        finally:
            sock.close()
    
    def responder_descoberta(self, request, gateway_addr):
        """Responde à solicitação de descoberta do Gateway"""
        try:
            response_port = request.get('response_port')
            if not response_port:
                print(f"[{self.device_id}] ❌ Porta de resposta não encontrada")
                return
            
            response = {
                'type': 'DISCOVERY_RESPONSE',
                'device_id': self.device_id,
                'device_type': self.device_type,
                'ip': self.ip,
                'grpc_port': self.grpc_port,
                'timestamp': datetime.now().isoformat(),
                'capabilities': self.get_capabilities()
            }
            
            # Enviar resposta para o Gateway
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(
                json.dumps(response).encode(),
                (gateway_addr[0], response_port)
            )
            sock.close()
            
            print(f"[{self.device_id}] ✅ Resposta enviada para Gateway na porta {response_port}")
            
        except Exception as e:
            print(f"[{self.device_id}] ❌ Erro ao responder descoberta: {e}")
    
    def get_capabilities(self):
        """Retorna capacidades do dispositivo - sobrescrito pelas subclasses"""
        return {}
    
    def simular_servidor_grpc(self):
        """Simula um servidor gRPC (não funcional, apenas para descoberta)"""
        print(f"[{self.device_id}] 🔧 Servidor gRPC simulado na porta {self.grpc_port}")
    
    def iniciar(self):
        """Inicia o atuador"""
        print(f"[{self.device_id}] 🚀 Iniciando {self.device_type}...")
        
        # Thread para escutar descoberta
        discovery_thread = threading.Thread(target=self.escutar_descoberta, daemon=True)
        discovery_thread.start()
        
        # Simular servidor gRPC
        grpc_thread = threading.Thread(target=self.simular_servidor_grpc, daemon=True)
        grpc_thread.start()
        
        return discovery_thread

class Camera(AtuadorBase):
    def __init__(self, device_id="CAM001"):
        super().__init__(device_id, "CAMERA", 50001)
        self.resolucao = "4K"
        self.gravando = False
        self.fps = 30
        self.zoom = 1.0
        
    def get_capabilities(self):
        return {
            'resolucoes': ['HD', '4K', '8K'],
            'fps_max': 60,
            'zoom_max': 10.0,
            'visao_noturna': True,
            'deteccao_movimento': True
        }

class PosteIluminacao(AtuadorBase):
    def __init__(self, device_id="POSTE001"):
        super().__init__(device_id, "POSTE_ILUMINACAO", 50002)
        self.intensidade = 75  # 0-100%
        self.ligado = True
        self.modo_automatico = True
        
    def get_capabilities(self):
        return {
            'potencia_max': '100W',
            'tipo_lampada': 'LED',
            'dimmer': True,
            'sensor_movimento': True,
            'sensor_luminosidade': True
        }

class Semaforo(AtuadorBase):
    def __init__(self, device_id="SEM001"):
        super().__init__(device_id, "SEMAFORO", 50003)
        self.estado_atual = "verde"
        self.tempo_verde = 45
        self.tempo_amarelo = 5
        self.tempo_vermelho = 40
        self.modo_emergencia = False
        
    def get_capabilities(self):
        return {
            'estados': ['verde', 'amarelo', 'vermelho'],
            'modo_emergencia': True,
            'sensor_fluxo': True,
            'controle_central': True
        }

def main():
    if len(sys.argv) < 2:
        print("Uso: python AtuadoresCidade.py <TIPO> [ID]")
        print("Tipos: CAMERA, POSTE, SEMAFORO, TODOS")
        print("Exemplo: python AtuadoresCidade.py CAMERA CAM001")
        return
    
    tipo = sys.argv[1].upper()
    device_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    atuadores = []
    threads = []
    
    try:
        if tipo == "CAMERA":
            cam = Camera(device_id or "CAM001")
            atuadores.append(cam)
            threads.append(cam.iniciar())
            
        elif tipo == "POSTE":
            poste = PosteIluminacao(device_id or "POSTE001")
            atuadores.append(poste)
            threads.append(poste.iniciar())
            
        elif tipo == "SEMAFORO":
            sem = Semaforo(device_id or "SEM001")
            atuadores.append(sem)
            threads.append(sem.iniciar())
            
        elif tipo == "TODOS":
            # Criar vários atuadores
            dispositivos = [
                Camera("CAM001"),
                Camera("CAM002"), 
                PosteIluminacao("POSTE001"),
                PosteIluminacao("POSTE002"),
                Semaforo("SEM001")
            ]
            
            for dispositivo in dispositivos:
                atuadores.append(dispositivo)
                threads.append(dispositivo.iniciar())
        
        else:
            print(f"❌ Tipo '{tipo}' não reconhecido")
            return
        
        print("\n" + "="*50)
        print("🏙️  ATUADORES CIDADE INTELIGENTE INICIADOS")
        print("="*50)
        print("Dispositivos ativos:")
        for atuador in atuadores:
            print(f"  • {atuador.device_id} ({atuador.device_type}) - porta gRPC {atuador.grpc_port}")
        print("Pressione Ctrl+C para parar...")
        
        # Manter o programa rodando
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Parando atuadores...")
        for atuador in atuadores:
            atuador.running = False
        print("Atuadores parados!")

if __name__ == "__main__":
    main()
