import pika
import json
import time
import random
import threading
import socket
from datetime import datetime

class SensorTemperatura:
    def __init__(self, sensor_id="TEMP001"):
        self.sensor_id = sensor_id
        self.temperatura = 20.0
        self.ativo = True
        self.intervalo = 15  # segundos
        self.connection = None
        self.channel = None
        
    def conectar_broker(self, broker_host='localhost', queue='sensor_temperatura'):
        """Conecta ao broker RabbitMQ"""
        try:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(broker_host)
            )
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=queue, durable=True)
            self.queue = queue
            print(f"[{self.sensor_id}] Conectado ao broker RabbitMQ")
            return True
        except Exception as e:
            print(f"[{self.sensor_id}] Erro ao conectar broker: {e}")
            return False
    
    def gerar_leitura(self):
        """Simula leitura de temperatura com variação realística"""
        # Variação de -2°C a +2°C
        variacao = random.uniform(-2.0, 2.0)
        self.temperatura = max(5.0, min(45.0, self.temperatura + variacao))
        
        return {
            'sensor_id': self.sensor_id,
            'tipo': 'temperatura',
            'valor': round(self.temperatura, 2),
            'unidade': '°C',
            'timestamp': datetime.now().isoformat(),
            'localizacao': 'Rua Principal, Centro'
        }
    
    def publicar_dados(self):
        """Publica dados no broker"""
        if not self.channel:
            return False
            
        try:
            dados = self.gerar_leitura()
            message = json.dumps(dados)
            
            self.channel.basic_publish(
                exchange='',
                routing_key=self.queue,
                body=message,
                properties=pika.BasicProperties(delivery_mode=2)  # Persistente
            )
            
            print(f"[{self.sensor_id}] 🌡️  Temperatura: {dados['valor']}°C")
            return True
            
        except Exception as e:
            print(f"[{self.sensor_id}] Erro ao publicar: {e}")
            return False
    
    def iniciar_monitoramento(self):
        """Inicia o loop de monitoramento"""
        def loop_sensor():
            while self.ativo:
                if self.publicar_dados():
                    time.sleep(self.intervalo)
                else:
                    print(f"[{self.sensor_id}] Tentando reconectar...")
                    time.sleep(5)
                    if not self.conectar_broker():
                        time.sleep(10)
        
        sensor_thread = threading.Thread(target=loop_sensor, daemon=True)
        sensor_thread.start()
        return sensor_thread

class SensorQualidadeAr:
    def __init__(self, sensor_id="AIR001"):
        self.sensor_id = sensor_id
        self.co2 = 400.0  # ppm (partes por milhão)
        self.pm25 = 15.0  # µg/m³ (microgramas por metro cúbico)
        self.pm10 = 25.0  # µg/m³
        self.ativo = True
        self.intervalo = 20  # segundos
        self.connection = None
        self.channel = None
        
    def conectar_broker(self, broker_host='localhost', queue='sensor_qualidade_ar'):
        """Conecta ao broker RabbitMQ"""
        try:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(broker_host)
            )
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=queue, durable=True)
            self.queue = queue
            print(f"[{self.sensor_id}] Conectado ao broker RabbitMQ")
            return True
        except Exception as e:
            print(f"[{self.sensor_id}] Erro ao conectar broker: {e}")
            return False
    
    def gerar_leitura(self):
        """Simula leitura de qualidade do ar"""
        # Simulação de variações realísticas baseadas na hora do dia
        hora_atual = datetime.now().hour
        
        # Padrões de poluição mais realísticos
        if 6 <= hora_atual <= 9 or 17 <= hora_atual <= 20:  # Rush hours
            variacao_co2 = random.uniform(20, 80)
            variacao_pm25 = random.uniform(2, 12)
            variacao_pm10 = random.uniform(3, 15)
        elif 22 <= hora_atual or hora_atual <= 5:  # Madrugada - melhor qualidade
            variacao_co2 = random.uniform(-30, 10)
            variacao_pm25 = random.uniform(-3, 2)
            variacao_pm10 = random.uniform(-5, 3)
        else:  # Demais horários
            variacao_co2 = random.uniform(-20, 40)
            variacao_pm25 = random.uniform(-2, 8)
            variacao_pm10 = random.uniform(-3, 10)
        
        # Aplica variações
        self.co2 = max(300, min(2000, self.co2 + variacao_co2))
        self.pm25 = max(5, min(200, self.pm25 + variacao_pm25))
        self.pm10 = max(8, min(300, self.pm10 + variacao_pm10))
        
        # Classificação da qualidade do ar baseada em padrões da OMS e EPA
        qualidade = self.classificar_qualidade_ar()
        
        return {
            'sensor_id': self.sensor_id,
            'tipo': 'qualidade_ar',
            'co2': round(self.co2, 1),
            'pm25': round(self.pm25, 1),
            'pm10': round(self.pm10, 1),
            'qualidade': qualidade,
            'nivel_risco': self.obter_nivel_risco(qualidade),
            'timestamp': datetime.now().isoformat(),
            'localizacao': 'Avenida Central, Centro'
        }
    
    def classificar_qualidade_ar(self):
        """Classifica a qualidade do ar baseada nos padrões internacionais"""
        pontuacao = 0
        
        # CO2 (ppm) - Padrões de conforto indoor/outdoor
        if self.co2 <= 400:
            pontuacao += 0  # Excelente
        elif self.co2 <= 600:
            pontuacao += 1  # Boa
        elif self.co2 <= 1000:
            pontuacao += 2  # Moderada
        elif self.co2 <= 1500:
            pontuacao += 3  # Ruim
        else:
            pontuacao += 4  # Péssima
        
        # PM2.5 (µg/m³) - Padrões OMS
        if self.pm25 <= 12:
            pontuacao += 0  # Excelente
        elif self.pm25 <= 25:
            pontuacao += 1  # Boa
        elif self.pm25 <= 50:
            pontuacao += 2  # Moderada
        elif self.pm25 <= 100:
            pontuacao += 3  # Ruim
        else:
            pontuacao += 4  # Péssima
        
        # PM10 (µg/m³) - Padrões OMS
        if self.pm10 <= 20:
            pontuacao += 0  # Excelente
        elif self.pm10 <= 40:
            pontuacao += 1  # Boa
        elif self.pm10 <= 80:
            pontuacao += 2  # Moderada
        elif self.pm10 <= 150:
            pontuacao += 3  # Ruim
        else:
            pontuacao += 4  # Péssima
        
        # Classificação final baseada na pontuação média
        media = pontuacao / 3
        
        if media <= 0.5:
            return "EXCELENTE"
        elif media <= 1.2:
            return "BOA"
        elif media <= 2.0:
            return "MODERADA"
        elif media <= 3.0:
            return "RUIM"
        else:
            return "PÉSSIMA"
    
    def obter_nivel_risco(self, qualidade):
        """Retorna nível de risco baseado na qualidade"""
        niveis = {
            "EXCELENTE": "Baixo",
            "BOA": "Baixo", 
            "MODERADA": "Médio",
            "RUIM": "Alto",
            "PÉSSIMA": "Muito Alto"
        }
        return niveis.get(qualidade, "Desconhecido")
        
        return {
            'sensor_id': self.sensor_id,
            'tipo': 'qualidade_ar',
            'co2': round(self.co2, 1),
            'pm25': round(self.pm25, 1),
            'pm10': round(self.pm10, 1),
            'qualidade': qualidade,
            'timestamp': datetime.now().isoformat(),
            'localizacao': 'Avenida Central, Centro'
        }
    
    def publicar_dados(self):
        """Publica dados no broker"""
        if not self.channel:
            return False
            
        try:
            dados = self.gerar_leitura()
            message = json.dumps(dados)
            
            self.channel.basic_publish(
                exchange='',
                routing_key=self.queue,
                body=message,
                properties=pika.BasicProperties(delivery_mode=2)  # Persistente
            )
            
            # Emojis e cores baseadas na qualidade
            emojis = {
                "EXCELENTE": "🟢",
                "BOA": "🟢", 
                "MODERADA": "🟡",
                "RUIM": "🟠",
                "PÉSSIMA": "🔴"
            }
            
            emoji = emojis.get(dados['qualidade'], "⚪")
            print(f"[{self.sensor_id}] {emoji} {dados['qualidade']} ({dados['nivel_risco']} risco) | CO2: {dados['co2']}ppm | PM2.5: {dados['pm25']}µg/m³ | PM10: {dados['pm10']}µg/m³")
            return True
            
        except Exception as e:
            print(f"[{self.sensor_id}] Erro ao publicar: {e}")
            return False
    
    def iniciar_monitoramento(self):
        """Inicia o loop de monitoramento"""
        def loop_sensor():
            while self.ativo:
                if self.publicar_dados():
                    time.sleep(self.intervalo)
                else:
                    print(f"[{self.sensor_id}] Tentando reconectar...")
                    time.sleep(5)
                    if not self.conectar_broker():
                        time.sleep(10)
        
        sensor_thread = threading.Thread(target=loop_sensor, daemon=True)
        sensor_thread.start()
        return sensor_thread

class SensorMulticast:
    """Classe para descoberta via multicast para sensores"""
    def __init__(self, sensor_id, sensor_type):
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
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
                
                print(f"[{self.sensor_id}] Escutando descoberta multicast em {self.multicast_group}:{self.multicast_port}")
            except Exception as e:
                print(f"[{self.sensor_id}] Erro ao configurar multicast: {e}")
                return
            
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    message = json.loads(data.decode())
                    
                    if message.get('type') == 'DISCOVERY_REQUEST':
                        print(f"[{self.sensor_id}] Recebida solicitação de descoberta de {addr}")
                        
                        # Responder com informações do sensor
                        response = {
                            'type': 'DISCOVERY_RESPONSE',
                            'device_type': 'SENSOR',
                            'sensor_type': self.sensor_type,
                            'device_id': self.sensor_id,
                            'ip': socket.gethostbyname(socket.gethostname()),
                            'capabilities': ['publish_data'],
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        # Registrar via HTTP também (mais confiável)
                        try:
                            import requests
                            gateway_url = f"http://{addr[0]}:5000/api/discovery/register"
                            requests.post(gateway_url, json=response, timeout=2)
                            print(f"[{self.sensor_id}] Registrado via HTTP no Gateway")
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
                        
                        print(f"[{self.sensor_id}] Resposta enviada para Gateway na porta {response_port}")
                        
                except Exception as e:
                    print(f"[{self.sensor_id}] Erro na descoberta: {e}")
        
        discovery_thread = threading.Thread(target=listen_discovery, daemon=True)
        discovery_thread.start()

def main():
    """Função principal para executar sensores"""
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python SensoresCidade.py <TIPO> [ID]")
        print("Tipos: TEMPERATURA, QUALIDADE_AR, TODOS")
        print("Exemplo: python SensoresCidade.py TEMPERATURA TEMP001")
        sys.exit(1)
    
    tipo = sys.argv[1].upper()
    sensor_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    sensors = []
    threads = []
    
    if tipo == "TEMPERATURA" or tipo == "TODOS":
        temp_id = sensor_id or "TEMP001"
        sensor_temp = SensorTemperatura(temp_id)
        
        # Descoberta multicast
        discovery_temp = SensorMulticast(temp_id, "TEMPERATURA")
        discovery_temp.start_discovery_listener()
        
        if sensor_temp.conectar_broker():
            thread = sensor_temp.iniciar_monitoramento()
            sensors.append(sensor_temp)
            threads.append(thread)
        
    if tipo == "QUALIDADE_AR" or tipo == "TODOS":
        air_id = sensor_id or "AIR001"
        sensor_air = SensorQualidadeAr(air_id)
        
        # Descoberta multicast
        discovery_air = SensorMulticast(air_id, "QUALIDADE_AR")
        discovery_air.start_discovery_listener()
        
        if sensor_air.conectar_broker():
            thread = sensor_air.iniciar_monitoramento()
            sensors.append(sensor_air)
            threads.append(thread)
    
    if not sensors:
        print("Nenhum sensor foi iniciado!")
        return
    
    print(f"\n{'='*50}")
    print(f"🏙️  SENSORES CIDADE INTELIGENTE INICIADOS")
    print(f"{'='*50}")
    print("Pressione Ctrl+C para parar...")
    
    try:
        # Manter o programa rodando
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Parando sensores...")
        for sensor in sensors:
            sensor.ativo = False
            if sensor.connection:
                sensor.connection.close()
        
        print("Sensores parados com sucesso!")

if __name__ == "__main__":
    main()
