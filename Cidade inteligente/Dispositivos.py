import grpc
import threading
import time
import socket
import json
import pika
from concurrent import futures
from datetime import datetime
import smart_city_pb2_grpc

# Importações dos protobuf (vou criar uma versão simplificada)
import smart_city_pb2

class ConfigCamera:
    def __init__(self, resolucao="HD"):
        self.resolucao = resolucao

class StatusCamera:
    def __init__(self, ligada=False, resolucao="HD", gravando=False):
        self.ligada = ligada
        self.resolucao = resolucao
        self.gravando = gravando

class StatusPoste:
    def __init__(self, lampada_ligada=False, intensidade=100):
        self.lampada_ligada = lampada_ligada
        self.intensidade = intensidade

class ConfigPoste:
    def __init__(self, intensidade=100):
        self.intensidade = intensidade

class StatusSemaforo:
    def __init__(self, estado_atual="VERMELHO", tempo_vermelho=30, tempo_verde=25, tempo_amarelo=5, funcionando=True):
        self.estado_atual = estado_atual
        self.tempo_vermelho = tempo_vermelho
        self.tempo_verde = tempo_verde
        self.tempo_amarelo = tempo_amarelo
        self.funcionando = funcionando

class ConfigSemaforo:
    def __init__(self, tempo_vermelho=30, tempo_verde=25, tempo_amarelo=5):
        self.tempo_vermelho = tempo_vermelho
        self.tempo_verde = tempo_verde
        self.tempo_amarelo = tempo_amarelo

# ================================
# CÂMERA INTELIGENTE
# ================================
class Camera:
    def __init__(self, device_id="CAM001"):
        self.device_id = device_id
        self.ligada = False
        self.resolucao = "HD"  # HD, FullHD, 4K
        self.gravando = False
        self.porta_grpc = 50052
        
    def Ligar(self, request, context):
        self.ligada = True
        print(f"[{self.device_id}] 📹 Câmera LIGADA - Status: ATIVA")
        return smart_city_pb2.Vazio()
    
    def Desligar(self, request, context):
        self.ligada = False
        self.gravando = False
        print(f"[{self.device_id}] 📹 Câmera DESLIGADA - Status: INATIVA")
        print(f"[{self.device_id}] ❌ Parando todas as operações da câmera")
        print(f"[{self.device_id}] 🔌 DESCONECTANDO do sistema - Processo será finalizado")
        
        # Finalizar processo após pequeno delay para enviar resposta
        import threading
        def finalizar():
            import time
            time.sleep(2)  # Aguarda 2 segundos para resposta ser enviada
            import os
            print(f"[{self.device_id}] 💀 Finalizando processo da câmera")
            os._exit(0)  # Força finalização do processo
        
        threading.Thread(target=finalizar, daemon=True).start()
        return smart_city_pb2.Vazio()
    
    def SetResolucao(self, request, context):
        if not self.ligada:
            print(f"[{self.device_id}] ❌ Câmera desligada - comando ignorado")
            return smart_city_pb2.Vazio()
            
        # request pode ser um objeto ou uma string
        if hasattr(request, 'resolucao'):
            resolucao = request.resolucao
        else:
            resolucao = str(request) if request else "HD"
            
        if resolucao in ["HD", "FullHD", "4K", "1080p"]:
            if resolucao == "1080p":
                resolucao = "FullHD"
            self.resolucao = resolucao
            print(f"[{self.device_id}] 📹 Resolução alterada para {self.resolucao}")
        return smart_city_pb2.Vazio()
    
    def IniciarGravacao(self, request, context):
        if not self.ligada:
            print(f"[{self.device_id}] ❌ Câmera desligada - não pode iniciar gravação")
            return smart_city_pb2.Vazio()
            
        if self.ligada:
            self.gravando = True
            print(f"[{self.device_id}] 🔴 Gravação INICIADA em {self.resolucao}")
        return smart_city_pb2.Vazio()
    
    def PararGravacao(self, request, context):
        self.gravando = False
        print(f"[{self.device_id}] ⏹️  Gravação PARADA")
        return smart_city_pb2.Vazio()
    
    def getStatus(self, request, context):
        status = {
            "ligada": self.ligada,
            "resolucao": self.resolucao,
            "gravando": self.gravando,
            "status": "ATIVA" if self.ligada else "INATIVA"
        }
        print(f"[{self.device_id}] 📊 Status solicitado: {status}")
        return StatusCamera(self.ligada, self.resolucao, self.gravando)

# ================================
# POSTE DE ILUMINAÇÃO
# ================================
class Poste:
    def __init__(self, device_id="POST001"):
        self.device_id = device_id
        self.poste_ativo = True  # Estado geral do poste
        self.lampada_ligada = False
        self.intensidade = 100  # 0-100%
        self.porta_grpc = 50053
        
    def LigarLampada(self, request, context):
        if not self.poste_ativo:
            print(f"[{self.device_id}] ❌ Poste inativo - comando ignorado")
            return smart_city_pb2.Vazio()
            
        self.lampada_ligada = True
        print(f"[{self.device_id}] 💡 Lâmpada LIGADA - Intensidade: {self.intensidade}%")
        print(f"[{self.device_id}] ✨ Iluminação pública ATIVA")
        return smart_city_pb2.Vazio()
    
    def DesligarLampada(self, request, context):
        self.lampada_ligada = False
        print(f"[{self.device_id}] 💡 Lâmpada DESLIGADA")
        print(f"[{self.device_id}] 🌙 Área escura - sem iluminação")
        print(f"[{self.device_id}] 🔌 DESCONECTANDO do sistema - Processo será finalizado")
        
        # Finalizar processo após pequeno delay para enviar resposta
        import threading
        def finalizar():
            import time
            time.sleep(2)  # Aguarda 2 segundos para resposta ser enviada
            import os
            print(f"[{self.device_id}] 💀 Finalizando processo do poste")
            os._exit(0)  # Força finalização do processo
        
        threading.Thread(target=finalizar, daemon=True).start()
        return smart_city_pb2.Vazio()
    
    def SetIntensidade(self, request, context):
        if not self.poste_ativo:
            print(f"[{self.device_id}] ❌ Poste inativo - comando ignorado")
            return smart_city_pb2.Vazio()
            
        if not self.lampada_ligada:
            print(f"[{self.device_id}] ⚠️  Lâmpada desligada - ligando automaticamente")
            self.lampada_ligada = True
            
        # request pode ser um objeto ou um número
        if hasattr(request, 'intensidade'):
            intensidade = request.intensidade
        else:
            try:
                intensidade = int(request) if request else 100
            except:
                intensidade = 100
                
        if 0 <= intensidade <= 100:
            old_intensidade = self.intensidade
            self.intensidade = intensidade
            print(f"[{self.device_id}] 💡 Intensidade: {old_intensidade}% → {self.intensidade}%")
            
            if intensidade == 0:
                self.lampada_ligada = False
                print(f"[{self.device_id}] 🌙 Lâmpada automaticamente desligada (intensidade 0%)")
                
        return smart_city_pb2.Vazio()
        
    def DesativarPoste(self, request, context):
        """Desativa completamente o poste - simula desconexão"""
        self.poste_ativo = False
        self.lampada_ligada = False
        print(f"[{self.device_id}] 🔌 POSTE DESATIVADO - Simulando desconexão")
        print(f"[{self.device_id}] ❌ Sistema offline - não responderá a comandos")
        return smart_city_pb2.Vazio()
        
    def AtivarPoste(self, request, context):
        """Reativa o poste"""
        self.poste_ativo = True
        print(f"[{self.device_id}] 🔌 POSTE REATIVADO - Sistema online")
        return smart_city_pb2.Vazio()
    
    def getStatus(self, request, context):
        status = {
            "poste_ativo": self.poste_ativo,
            "lampada_ligada": self.lampada_ligada,
            "intensidade": self.intensidade,
            "status": "ONLINE" if self.poste_ativo else "OFFLINE"
        }
        print(f"[{self.device_id}] 📊 Status solicitado: {status}")
        return StatusPoste(self.lampada_ligada, self.intensidade)

# ================================
# SEMÁFORO INTELIGENTE
# ================================
class Semaforo:
    def __init__(self, device_id="SEM001"):
        self.device_id = device_id
        self.sistema_ativo = True  # Sistema geral
        self.funcionando = True    # Funcionamento do semáforo
        self.estado_atual = "VERMELHO"
        self.tempo_vermelho = 30  # segundos
        self.tempo_verde = 25     # segundos
        self.tempo_amarelo = 5    # segundos
        self.ciclo_thread = None
        self.modo_emergencia = False
        self.porta_grpc = 50054
        
    def Ligar(self, request, context):
        if not self.sistema_ativo:
            print(f"[{self.device_id}] ❌ Sistema inativo - comando ignorado")
            return smart_city_pb2.Vazio()
            
        self.funcionando = True
        self.modo_emergencia = False
        self._iniciar_ciclo()
        print(f"[{self.device_id}] 🚦 Semáforo LIGADO - Iniciando ciclo normal")
        return smart_city_pb2.Vazio()
    
    def Desligar(self, request, context):
        self.funcionando = False
        self.modo_emergencia = False
        if self.ciclo_thread:
            self.ciclo_thread = None
        print(f"[{self.device_id}] 🚦 Semáforo DESLIGADO - Todas as luzes apagadas")
        print(f"[{self.device_id}] ⚠️  ATENÇÃO: Cruzamento sem sinalização!")
        print(f"[{self.device_id}] 🔌 DESCONECTANDO do sistema - Processo será finalizado")
        
        # Finalizar processo após pequeno delay para enviar resposta
        import threading
        def finalizar():
            import time
            time.sleep(2)  # Aguarda 2 segundos para resposta ser enviada
            import os
            print(f"[{self.device_id}] 💀 Finalizando processo do semáforo")
            os._exit(0)  # Força finalização do processo
        
        threading.Thread(target=finalizar, daemon=True).start()
        return smart_city_pb2.Vazio()
        
    def DesativarSistema(self, request, context):
        """Desativa completamente o sistema do semáforo"""
        self.sistema_ativo = False
        self.funcionando = False
        self.modo_emergencia = False
        if self.ciclo_thread:
            self.ciclo_thread = None
        print(f"[{self.device_id}] 🔌 SISTEMA DESATIVADO - Simulando desconexão total")
        print(f"[{self.device_id}] ❌ Offline - não responderá a comandos")
        return smart_city_pb2.Vazio()
        
    def AtivarSistema(self, request, context):
        """Reativa o sistema do semáforo"""
        self.sistema_ativo = True
        print(f"[{self.device_id}] 🔌 SISTEMA REATIVADO - Online novamente")
        return smart_city_pb2.Vazio()
    
    def SetTempos(self, request, context):
        # request pode ser um objeto com atributos ou um dict
        if hasattr(request, 'tempo_vermelho'):
            self.tempo_vermelho = request.tempo_vermelho
            self.tempo_verde = request.tempo_verde
            self.tempo_amarelo = request.tempo_amarelo
        elif isinstance(request, dict):
            self.tempo_vermelho = request.get('tempo_vermelho', 30)
            self.tempo_verde = request.get('tempo_verde', 25)
            self.tempo_amarelo = request.get('tempo_amarelo', 5)
        
        print(f"[{self.device_id}] Tempos alterados - V:{self.tempo_vermelho}s G:{self.tempo_verde}s A:{self.tempo_amarelo}s")
        return smart_city_pb2.Vazio()
    
    def ModoEmergencia(self, request, context):
        if not self.sistema_ativo:
            print(f"[{self.device_id}] ❌ Sistema inativo - comando ignorado")
            return smart_city_pb2.Vazio()
            
        self.modo_emergencia = True
        self.estado_atual = "AMARELO"
        self.funcionando = False
        if self.ciclo_thread:
            self.ciclo_thread = None
        print(f"[{self.device_id}] 🚨 MODO EMERGÊNCIA ATIVADO - Amarelo intermitente")
        return smart_city_pb2.Vazio()
    
    def EmergenciaAmareloIntermitente(self, request, context):
        """Alias para ModoEmergencia"""
        return self.ModoEmergencia(request, context)
        
    def Status(self, request, context):
        if not self.sistema_ativo:
            status = "SISTEMA_OFFLINE"
            estado = "DESCONECTADO"
        elif not self.funcionando and self.modo_emergencia:
            status = "EMERGENCIA"
            estado = "AMARELO_INTERMITENTE"
        elif self.funcionando:
            status = "OPERACIONAL"
            estado = self.estado_atual
        else:
            status = "DESLIGADO"
            estado = "TODAS_APAGADAS"
            
        print(f"[{self.device_id}] Status: {status} | Estado: {estado}")
        return smart_city_pb2.Status(
            status=status,
            device_id=self.device_id,
            timestamp=str(int(time.time())),
            details=f"Estado: {estado}, Sistema: {'Ativo' if self.sistema_ativo else 'Inativo'}"
        )
    
    def getStatus(self, request, context):
        return StatusSemaforo(
            self.estado_atual, 
            self.tempo_vermelho, 
            self.tempo_verde, 
            self.tempo_amarelo, 
            self.funcionando
        )
    
    def _iniciar_ciclo(self):
        def ciclo_semaforo():
            while self.funcionando and not self.modo_emergencia:
                # Vermelho
                self.estado_atual = "VERMELHO"
                print(f"[{self.device_id}] 🔴 VERMELHO - {self.tempo_vermelho}s")
                time.sleep(self.tempo_vermelho)
                
                if not self.funcionando or self.modo_emergencia:
                    break
                    
                # Verde
                self.estado_atual = "VERDE"
                print(f"[{self.device_id}] 🟢 VERDE - {self.tempo_verde}s")
                time.sleep(self.tempo_verde)
                
                if not self.funcionando or self.modo_emergencia:
                    break
                    
                # Amarelo
                self.estado_atual = "AMARELO"
                print(f"[{self.device_id}] 🟡 AMARELO - {self.tempo_amarelo}s")
                time.sleep(self.tempo_amarelo)
        
        if self.ciclo_thread is None or not self.ciclo_thread.is_alive():
            self.ciclo_thread = threading.Thread(target=ciclo_semaforo, daemon=True)
            self.ciclo_thread.start()

# ================================
# DESCOBERTA MULTICAST
# ================================
class MulticastDiscovery:
    def __init__(self, device_type, device_id, grpc_port):
        self.device_type = device_type
        self.device_id = device_id
        self.grpc_port = grpc_port
        self.multicast_group = '224.0.0.1'
        self.multicast_port = 10000
        
    def start_discovery_listener(self):
        def listen_discovery():
            try:
                # Socket para receber descoberta
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                
                # Permitir reutilização da porta
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                
                sock.bind(('', self.multicast_port))
                
                # Juntar ao grupo multicast
                mreq = socket.inet_aton(self.multicast_group) + socket.inet_aton('0.0.0.0')
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            except Exception as e:
                print(f"[{self.device_id}] Erro ao configurar multicast: {e}")
                return
            
            print(f"[{self.device_id}] Escutando descoberta multicast em {self.multicast_group}:{self.multicast_port}")
            
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    message = json.loads(data.decode())
                    
                    if message.get('type') == 'DISCOVERY_REQUEST':
                        print(f"[{self.device_id}] Recebida solicitação de descoberta de {addr}")
                        
                        # Responder com informações do dispositivo
                        response = {
                            'type': 'DISCOVERY_RESPONSE',
                            'device_type': self.device_type,
                            'device_id': self.device_id,
                            'ip': '127.0.0.1',  # Usar localhost para compatibilidade
                            'grpc_port': self.grpc_port,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        # Registrar via HTTP também (mais confiável)
                        try:
                            import requests
                            gateway_url = f"http://{addr[0]}:5000/api/discovery/register"
                            requests.post(gateway_url, json=response, timeout=2)
                            print(f"[{self.device_id}] Registrado via HTTP no Gateway")
                        except:
                            pass  # Falha silenciosa se HTTP não funcionar
                        
                        # Usar porta de resposta especificada ou porta de origem (UDP)
                        response_port = message.get('response_port', addr[1])
                        
                        # Enviar resposta UDP também
                        response_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        response_sock.sendto(
                            json.dumps(response).encode(), 
                            (addr[0], response_port)
                        )
                        response_sock.close()
                        
                        print(f"[{self.device_id}] Resposta enviada para Gateway na porta {response_port}")
                        
                except Exception as e:
                    print(f"[{self.device_id}] Erro na descoberta: {e}")
        
        discovery_thread = threading.Thread(target=listen_discovery, daemon=True)
        discovery_thread.start()

# ================================
# SERVICER CLASSES PARA GRPC
# ================================
class CameraServicer:
    def __init__(self, camera):
        self.camera = camera
    
    def Ligar(self, request, context):
        return self.camera.Ligar(request, context)
    
    def Desligar(self, request, context):
        return self.camera.Desligar(request, context)
    
    def SetResolucao(self, request, context):
        return self.camera.SetResolucao(request, context)
    
    def IniciarGravacao(self, request, context):
        return self.camera.IniciarGravacao(request, context)
    
    def PararGravacao(self, request, context):
        return self.camera.PararGravacao(request, context)
    
    def getStatus(self, request, context):
        return self.camera.getStatus(request, context)

class PosteServicer:
    def __init__(self, poste):
        self.poste = poste
    
    def LigarLampada(self, request, context):
        return self.poste.LigarLampada(request, context)
    
    def DesligarLampada(self, request, context):
        return self.poste.DesligarLampada(request, context)
    
    def SetIntensidade(self, request, context):
        return self.poste.SetIntensidade(request, context)
    
    def getStatus(self, request, context):
        return self.poste.getStatus(request, context)

class SemaforoServicer:
    def __init__(self, semaforo):
        self.semaforo = semaforo
    
    def Ligar(self, request, context):
        return self.semaforo.Ligar(request, context)
    
    def Desligar(self, request, context):
        return self.semaforo.Desligar(request, context)
    
    def SetTempos(self, request, context):
        return self.semaforo.SetTempos(request, context)
    
    def ModoEmergencia(self, request, context):
        return self.semaforo.ModoEmergencia(request, context)
    
    def getStatus(self, request, context):
        return self.semaforo.getStatus(request, context)

# ================================
# SERVIDOR GRPC PARA DISPOSITIVOS
# ================================
def serve_device(device_type, device_id, port):
    """Inicia servidor gRPC para um dispositivo específico"""
    
    # Descoberta multicast
    discovery = MulticastDiscovery(device_type, device_id, port)
    discovery.start_discovery_listener()
    
    # Servidor gRPC
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    device_instance = None
    
    if device_type == "CAMERA":
        camera = Camera(device_id)
        camera_servicer = CameraServicer(camera)
        device_instance = camera
        # Usar a função gerada pelo protobuf
        smart_city_pb2_grpc.add_CameraServicer_to_server(camera_servicer, server)
        print(f"[{device_id}] Câmera iniciada na porta {port}")
        
    elif device_type == "POSTE":
        poste = Poste(device_id)
        poste_servicer = PosteServicer(poste)
        device_instance = poste
        # Usar a função gerada pelo protobuf
        smart_city_pb2_grpc.add_PosteServicer_to_server(poste_servicer, server)
        print(f"[{device_id}] Poste iniciado na porta {port}")
        
    elif device_type == "SEMAFORO":
        semaforo = Semaforo(device_id)
        semaforo_servicer = SemaforoServicer(semaforo)
        device_instance = semaforo
        # Usar a função gerada pelo protobuf
        smart_city_pb2_grpc.add_SemaforoServicer_to_server(semaforo_servicer, server)
        semaforo.Ligar(None, None)  # Iniciar ciclo automaticamente
        print(f"[{device_id}] Semáforo iniciado na porta {port}")
    
    try:
        server.add_insecure_port(f'127.0.0.1:{port}')
        server.start()
        print(f"[{device_id}] Servidor gRPC rodando na porta {port}")
    except Exception as e:
        print(f"[{device_id}] ERRO: Não foi possível iniciar servidor gRPC na porta {port}: {e}")
        print(f"[{device_id}] Tentando apenas descoberta multicast sem gRPC...")
        # Continua apenas com descoberta multicast
    
    try:
        while True:
            time.sleep(86400)  # 24 horas
    except KeyboardInterrupt:
        print(f"[{device_id}] Parando servidor...")
        server.stop(0)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 4:
        print("Uso: python Dispositivos.py <TIPO> <ID> <PORTA>")
        print("Tipos: CAMERA, POSTE, SEMAFORO")
        print("Exemplo: python Dispositivos.py CAMERA CAM001 50052")
        sys.exit(1)
    
    device_type = sys.argv[1]
    device_id = sys.argv[2]
    port = int(sys.argv[3])
    
    if device_type not in ["CAMERA", "POSTE", "SEMAFORO"]:
        print("Tipo de dispositivo inválido. Use: CAMERA, POSTE, SEMAFORO")
        sys.exit(1)
    
    serve_device(device_type, device_id, port)
