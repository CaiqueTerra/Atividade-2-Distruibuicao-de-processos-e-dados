import grpc
import socket
import json
import time
import threading
import pika
from flask import Flask, jsonify, request, render_template
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import smart_city_pb2
import smart_city_pb2_grpc

class GatewayInteligente:
    def __init__(self):
        self.dispositivos_conectados = {}
        self.sensores_dados = {
            'temperatura': [],
            'qualidade_ar': []
        }
        self.broker_connection = None
        self.broker_channel = None
        self.multicast_group = '224.0.0.1'
        self.multicast_port = 10000
        self.web_port = 5000
        self.running = True  # Adicionar atributo running
        
        # Sistema de health check - verifica dispositivos a cada 60 segundos
        self.health_check_interval = 60
        self.health_check_timeout = 5
        self.last_health_check = time.time()
        
        # Thread para health check em background
        self.health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_check_thread.start()
        
        # Flask app
        self.app = Flask(__name__)
        self.setup_routes()
        
    def setup_routes(self):
        """Configura as rotas do serviço web"""
        
        @self.app.route('/')
        def home():
            return render_template('gateway_home.html')
        
        @self.app.route('/test')
        def test_charts():
            return render_template('test_charts.html')
            
        @self.app.route('/test_simple')
        def test_simple():
            return render_template('test_simple.html')
        
        @self.app.route('/api/dispositivos', methods=['GET'])
        def listar_dispositivos():
            """Lista todos os dispositivos conectados"""
            # Dispositivos gRPC (câmeras, postes, semáforos) - filtra apenas dispositivos reais
            dispositivos_grpc = []
            for device in self.dispositivos_conectados.values():
                # Incluir apenas dispositivos que NÃO são sensores
                if device['tipo'] not in ['SENSOR_TEMPERATURA', 'SENSOR_QUALIDADE_AR', 'SENSOR']:
                    dispositivos_grpc.append(device)
            
            # Sensores RabbitMQ (se tiver dados recentes) - fonte única de verdade para sensores
            sensores_rabbitmq = []
            
            # Sensor de temperatura
            if self.sensores_dados['temperatura']:
                ultima_temp = self.sensores_dados['temperatura'][-1]
                sensores_rabbitmq.append({
                    'id': ultima_temp.get('sensor_id', 'TEMP001'),
                    'tipo': 'SENSOR_TEMPERATURA',
                    'protocolo': 'RabbitMQ',
                    'ip': '127.0.0.1',
                    'porta_amqp': 5672,
                    'queue': 'sensor_temperatura',
                    'endereco': 'RabbitMQ:sensor_temperatura',
                    'ultima_leitura': ultima_temp.get('timestamp'),
                    'valor_atual': f"{ultima_temp.get('valor', 'N/A')}°C"
                })
            
            # Sensor de qualidade do ar
            if self.sensores_dados['qualidade_ar']:
                ultimo_ar = self.sensores_dados['qualidade_ar'][-1]
                sensores_rabbitmq.append({
                    'id': ultimo_ar.get('sensor_id', 'AIR001'),
                    'tipo': 'SENSOR_QUALIDADE_AR',
                    'protocolo': 'RabbitMQ',
                    'ip': '127.0.0.1',
                    'porta_amqp': 5672,
                    'queue': 'sensor_qualidade_ar',
                    'endereco': 'RabbitMQ:sensor_qualidade_ar',
                    'ultima_leitura': ultimo_ar.get('timestamp'),
                    'valor_atual': ultimo_ar.get('qualidade', 'N/A'),
                    'nivel_risco': ultimo_ar.get('nivel_risco', 'Baixo'),
                    'co2': ultimo_ar.get('co2', 0),
                    'pm25': ultimo_ar.get('pm25', 0),
                    'pm10': ultimo_ar.get('pm10', 0)
                })
            
            # Combinar todos os dispositivos
            todos_dispositivos = dispositivos_grpc + sensores_rabbitmq
            
            # Debug: log para entender o que está sendo retornado
            print(f"🔍 API /dispositivos: {len(dispositivos_grpc)} gRPC + {len(sensores_rabbitmq)} RabbitMQ = {len(todos_dispositivos)} total")
            
            return jsonify({
                'dispositivos': todos_dispositivos,
                'total': len(todos_dispositivos),
                'grpc_devices': len(dispositivos_grpc),
                'rabbitmq_sensors': len(sensores_rabbitmq),
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/api/dispositivos/<device_id>/status', methods=['GET'])
        def status_dispositivo(device_id):
            """Consulta status de um dispositivo específico"""
            if device_id not in self.dispositivos_conectados:
                return jsonify({'erro': 'Dispositivo não encontrado'}), 404
            
            dispositivo = self.dispositivos_conectados[device_id]
            try:
                # Aqui seria a chamada gRPC real para getStatus
                status = self.get_device_status_grpc(device_id)
                return jsonify({
                    'device_id': device_id,
                    'status': status,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({'erro': str(e)}), 500
        
        @self.app.route('/api/camera/<device_id>/controle', methods=['POST'])
        def controlar_camera(device_id):
            """Controla câmera via gRPC"""
            data = request.get_json()
            acao = data.get('acao')
            
            try:
                if acao == 'ligar':
                    result = self.camera_ligar_grpc(device_id)
                elif acao == 'desligar':
                    result = self.camera_desligar_grpc(device_id)
                elif acao == 'resolucao':
                    resolucao = data.get('resolucao', 'HD')
                    result = self.camera_set_resolucao_grpc(device_id, resolucao)
                elif acao == 'gravar':
                    result = self.camera_iniciar_gravacao_grpc(device_id)
                elif acao == 'parar_gravacao':
                    result = self.camera_parar_gravacao_grpc(device_id)
                else:
                    return jsonify({'erro': 'Ação inválida'}), 400
                
                return jsonify({
                    'sucesso': True,
                    'acao': acao,
                    'device_id': device_id,
                    'resultado': result
                })
                
            except Exception as e:
                return jsonify({'erro': str(e)}), 500
        
        @self.app.route('/api/poste/<device_id>/controle', methods=['POST'])
        def controlar_poste(device_id):
            """Controla poste via gRPC"""
            data = request.get_json()
            acao = data.get('acao')
            
            try:
                if acao == 'ligar':
                    result = self.poste_ligar_lampada_grpc(device_id)
                elif acao == 'desligar':
                    result = self.poste_desligar_lampada_grpc(device_id)
                elif acao == 'intensidade':
                    intensidade = data.get('intensidade', 100)
                    result = self.poste_set_intensidade_grpc(device_id, intensidade)
                else:
                    return jsonify({'erro': 'Ação inválida'}), 400
                
                return jsonify({
                    'sucesso': True,
                    'acao': acao,
                    'device_id': device_id,
                    'resultado': result
                })
                
            except Exception as e:
                return jsonify({'erro': str(e)}), 500
        
        @self.app.route('/api/semaforo/<device_id>/controle', methods=['POST'])
        def controlar_semaforo(device_id):
            """Controla semáforo via gRPC"""
            data = request.get_json()
            acao = data.get('acao')
            
            try:
                if acao == 'ligar':
                    result = self.semaforo_ligar_grpc(device_id)
                elif acao == 'desligar':
                    result = self.semaforo_desligar_grpc(device_id)
                elif acao == 'emergencia':
                    result = self.semaforo_modo_emergencia_grpc(device_id)
                elif acao == 'tempos':
                    tempos = data.get('tempos', {})
                    result = self.semaforo_set_tempos_grpc(device_id, tempos)
                else:
                    return jsonify({'erro': 'Ação inválida'}), 400
                
                return jsonify({
                    'sucesso': True,
                    'acao': acao,
                    'device_id': device_id,
                    'resultado': result
                })
                
            except Exception as e:
                return jsonify({'erro': str(e)}), 500
        
        @self.app.route('/api/sensores/dados', methods=['GET'])
        def dados_sensores():
            """Retorna dados dos sensores"""
            return jsonify({
                'temperatura': self.sensores_dados['temperatura'][-50:],  # Últimas 50 leituras
                'qualidade_ar': self.sensores_dados['qualidade_ar'][-50:],
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/api/discovery/register', methods=['POST'])
        def register_device():
            """Permite que dispositivos se registrem via HTTP"""
            data = request.get_json()
            
            if data and data.get('type') == 'DISCOVERY_RESPONSE':
                device_id = data.get('device_id')
                device_type = data.get('device_type')
                
                self.dispositivos_conectados[device_id] = {
                    'id': device_id,
                    'tipo': device_type,
                    'ip': data.get('ip'),
                    'porta_grpc': data.get('grpc_port'),
                    'timestamp_descoberta': datetime.now().isoformat(),
                    'endereco': f"{data.get('ip')}:{data.get('grpc_port', 'N/A')}"
                }
                
                print(f"✅ Dispositivo registrado via HTTP: {device_id} ({device_type})")
                return jsonify({'success': True, 'message': 'Device registered'})
            
            return jsonify({'error': 'Invalid registration data'}), 400
        
        @self.app.route('/api/discovery/descobrir', methods=['POST'])
        def descobrir_dispositivos_api():
            """Força uma nova descoberta de dispositivos"""
            result = self.descobrir_dispositivos()
            return jsonify({
                'descoberta_iniciada': True,
                'total_encontrados': len(self.dispositivos_conectados),
                'dispositivos': list(self.dispositivos_conectados.values()),
                'timestamp': datetime.now().isoformat()
            })

        @self.app.route('/api/discovery/force', methods=['POST'])
        def force_discovery():
            """Força uma nova descoberta de dispositivos"""
            result = self.descobrir_dispositivos()
            return jsonify({
                'discovery_triggered': True,
                'devices_found': len(self.dispositivos_conectados),
                'devices': list(self.dispositivos_conectados.values()),
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/api/debug', methods=['GET'])
        def debug_status():
            """Retorna informações de debug do Gateway"""
            return jsonify({
                'total_devices': len(self.dispositivos_conectados),
                'devices': list(self.dispositivos_conectados.values()),
                'sensor_data_count': {
                    'temperatura': len(self.sensores_dados['temperatura']),
                    'qualidade_ar': len(self.sensores_dados['qualidade_ar'])
                },
                'timestamp': datetime.now().isoformat()
            })
    
    def conectar_broker(self):
        """Conecta ao broker RabbitMQ"""
        try:
            self.broker_connection = pika.BlockingConnection(
                pika.ConnectionParameters('localhost')
            )
            self.broker_channel = self.broker_connection.channel()
            
            # Declarar filas
            self.broker_channel.queue_declare(queue='sensor_temperatura', durable=True)
            self.broker_channel.queue_declare(queue='sensor_qualidade_ar', durable=True)
            
            print("🔗 Gateway conectado ao broker RabbitMQ")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao conectar ao broker: {e}")
            return False
    
    def iniciar_consumidores(self):
        """Inicia consumidores para receber dados dos sensores"""
        
        def callback_temperatura(ch, method, properties, body):
            try:
                dados = json.loads(body.decode())
                self.sensores_dados['temperatura'].append(dados)
                
                # Manter apenas últimas 100 leituras
                if len(self.sensores_dados['temperatura']) > 100:
                    self.sensores_dados['temperatura'] = self.sensores_dados['temperatura'][-100:]
                
                print(f"📊 Temperatura recebida: {dados['valor']}°C de {dados['sensor_id']}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                
            except Exception as e:
                print(f"❌ Erro ao processar temperatura: {e}")
        
        def callback_qualidade_ar(ch, method, properties, body):
            try:
                dados = json.loads(body.decode())
                self.sensores_dados['qualidade_ar'].append(dados)
                
                # Manter apenas últimas 100 leituras
                if len(self.sensores_dados['qualidade_ar']) > 100:
                    self.sensores_dados['qualidade_ar'] = self.sensores_dados['qualidade_ar'][-100:]
                
                # Emojis baseados na qualidade
                emojis = {
                    "EXCELENTE": "🟢",
                    "BOA": "🟢", 
                    "MODERADA": "🟡",
                    "RUIM": "🟠",
                    "PÉSSIMA": "🔴"
                }
                
                emoji = emojis.get(dados.get('qualidade', 'BOA'), "🌬️")
                nivel_risco = dados.get('nivel_risco', 'Baixo')
                print(f"{emoji} Qualidade: {dados['qualidade']} ({nivel_risco} risco) | CO2: {dados['co2']}ppm | PM2.5: {dados['pm25']}µg/m³ de {dados['sensor_id']}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                
            except Exception as e:
                print(f"❌ Erro ao processar qualidade do ar: {e}")
        
        # Configurar consumidores
        self.broker_channel.basic_consume(
            queue='sensor_temperatura',
            on_message_callback=callback_temperatura
        )
        
        self.broker_channel.basic_consume(
            queue='sensor_qualidade_ar',
            on_message_callback=callback_qualidade_ar
        )
        
        # Iniciar consumo em thread separada
        def start_consuming():
            print("🎯 Iniciando consumo de dados dos sensores...")
            self.broker_channel.start_consuming()
        
        consume_thread = threading.Thread(target=start_consuming, daemon=True)
        consume_thread.start()
    
    def descobrir_dispositivos(self):
        """Envia solicitação de descoberta via multicast UDP"""
        try:
            # Limpar lista atual antes da nova descoberta
            dispositivos_descobertos = {}
            
            # Socket multicast
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(0.2)
            
            # TTL para multicast
            ttl = 2
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
            
            # Socket para receber respostas
            response_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            response_sock.bind(('', 0))  # Porta automática
            response_port = response_sock.getsockname()[1]
            
            # Mensagem de descoberta
            discovery_message = {
                'type': 'DISCOVERY_REQUEST',
                'gateway_id': 'GATEWAY_MAIN',
                'response_port': response_port,  # Incluir porta de resposta
                'timestamp': datetime.now().isoformat(),
                'broker_info': {
                    'host': 'localhost',
                    'port': 5672,
                    'queues': {
                        'temperatura': 'sensor_temperatura',
                        'qualidade_ar': 'sensor_qualidade_ar'
                    }
                }
            }
            
            message = json.dumps(discovery_message).encode()
            
            # Enviar descoberta
            print("📡 Enviando solicitação de descoberta multicast...")
            sock.sendto(message, (self.multicast_group, self.multicast_port))
            
            # Timeout para respostas
            response_sock.settimeout(5.0)
            
            print(f"👂 Aguardando respostas na porta {response_port}...")
            
            start_time = time.time()
            dispositivos_encontrados = 0
            
            while time.time() - start_time < 5:  # 5 segundos
                try:
                    data, addr = response_sock.recvfrom(1024)
                    response = json.loads(data.decode())
                    
                    if response.get('type') == 'DISCOVERY_RESPONSE':
                        device_id = response.get('device_id')
                        device_type = response.get('device_type')
                        
                        dispositivos_descobertos[device_id] = {
                            'id': device_id,
                            'tipo': device_type,
                            'ip': response.get('ip'),
                            'porta_grpc': response.get('grpc_port'),
                            'timestamp_descoberta': datetime.now().isoformat(),
                            'endereco': f"{response.get('ip')}:{response.get('grpc_port', 'N/A')}"
                        }
                        
                        dispositivos_encontrados += 1
                        print(f"✅ Dispositivo encontrado: {device_id} ({device_type}) em {addr[0]}")
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"❌ Erro ao receber resposta: {e}")
            
            sock.close()
            response_sock.close()
            
            # Substituir lista completa (remove dispositivos desconectados)
            self.dispositivos_conectados = dispositivos_descobertos
            
            print(f"🎯 Descoberta concluída: {dispositivos_encontrados} dispositivos encontrados")
            return dispositivos_encontrados > 0
            
        except Exception as e:
            print(f"❌ Erro na descoberta multicast: {e}")
            return False
    
    # ================================
    # MÉTODOS gRPC (Simulados)
    # ================================
    def get_device_status_grpc(self, device_id):
        """Simula chamada gRPC para obter status detalhado do dispositivo"""
        print(f"🔍 Consultando status detalhado de {device_id} via gRPC")
        
        dispositivo = self.dispositivos_conectados.get(device_id)
        if not dispositivo:
            return {"erro": "Dispositivo não encontrado"}
        
        tipo = dispositivo.get('tipo', 'UNKNOWN')
        base_status = {
            "device_id": device_id,
            "nome": dispositivo.get('nome', device_id),
            "tipo": tipo,
            "endereco": dispositivo.get('endereco', 'N/A'),
            "porta": dispositivo.get('porta', 'N/A'),
            "status_conexao": "online",
            "uptime": "2h 34m 12s",
            "ultima_comunicacao": datetime.now().isoformat(),
            "versao_firmware": "v2.1.4",
            "temperatura_interna": f"{20 + (hash(device_id) % 15)}°C"
        }
        
        # Status específico por tipo de dispositivo
        if tipo == 'CAMERA':
            base_status.update({
                "resolucao": "4K (3840x2160)",
                "fps": 30,
                "zoom": "2.5x",
                "modo_gravacao": "continuo",
                "espaco_storage": "78% usado (156GB/200GB)",
                "modo_visao_noturna": True,
                "deteccao_movimento": True,
                "angulo_visao": "120°",
                "qualidade_imagem": "excelente",
                "codec_video": "H.265",
                "bitrate": "15 Mbps",
                "status_leds": {
                    "led_power": "verde",
                    "led_network": "verde",
                    "led_recording": "vermelho_piscando"
                }
            })
        
        elif tipo == 'POSTE_ILUMINACAO':
            intensidade = 45 + (hash(device_id) % 50)  # 45-95%
            base_status.update({
                "intensidade_luz": f"{intensidade}%",
                "modo_operacao": "automatico",
                "sensor_luminosidade": f"{300 + (hash(device_id) % 200)} lux",
                "consumo_energia": f"{85 + (hash(device_id) % 30)}W",
                "temperatura_led": f"{45 + (hash(device_id) % 20)}°C",
                "horas_funcionamento": "2847h",
                "vida_util_restante": "87%",
                "tipo_lampada": "LED Full Spectrum 100W",
                "cor_temperatura": "4000K (branco neutro)",
                "sensor_movimento": True,
                "programacao": {
                    "acender": "18:30",
                    "apagar": "06:00",
                    "modo_noturno": "ativo"
                },
                "manutencao": {
                    "proxima_manutencao": "2025-09-15",
                    "ultima_limpeza": "2025-06-20"
                }
            })
        
        elif tipo == 'SEMAFORO':
            estados = ['verde', 'amarelo', 'vermelho']
            estado_atual = estados[hash(device_id) % 3]
            base_status.update({
                "estado_atual": estado_atual,
                "tempo_restante": f"{15 + (hash(device_id) % 45)}s",
                "modo_operacao": "temporizado",
                "ciclo_completo": "90s",
                "tempos_programados": {
                    "verde": "45s",
                    "amarelo": "5s", 
                    "vermelho": "40s"
                },
                "sensor_fluxo": True,
                "veiculos_detectados": hash(device_id) % 8,
                "pedestres_aguardando": hash(device_id) % 4,
                "modo_emergencia": False,
                "controle_central": True,
                "lampadas_status": {
                    "led_vermelho": "funcionando",
                    "led_amarelo": "funcionando", 
                    "led_verde": "funcionando",
                    "led_pedestre": "funcionando"
                },
                "historico_24h": {
                    "total_ciclos": 1440,
                    "interrupcoes": 0,
                    "modo_emergencia_ativado": 2
                }
            })
        
        elif tipo == 'SENSOR':
            # Para sensores RabbitMQ, pegar dados reais se disponíveis
            if device_id.startswith('TEMP'):
                dados_temp = self.sensores_dados.get('temperatura', [])
                ultimo_valor = dados_temp[-1]['valor'] if dados_temp else 20.0
                base_status.update({
                    "tipo_sensor": "Temperatura",
                    "valor_atual": f"{ultimo_valor:.1f}°C",
                    "unidade": "Celsius",
                    "precisao": "±0.1°C",
                    "faixa_operacao": "-40°C a +85°C",
                    "calibracao": "2025-03-15",
                    "intervalo_leitura": "10s",
                    "total_leituras_24h": 8640,
                    "valor_minimo_24h": f"{ultimo_valor - 5:.1f}°C",
                    "valor_maximo_24h": f"{ultimo_valor + 8:.1f}°C",
                    "tendencia": "estável",
                    "alarmes": {
                        "temperatura_alta": "desabilitado",
                        "temperatura_baixa": "desabilitado",
                        "falha_comunicacao": "ativo"
                    }
                })
            
            elif device_id.startswith('AIR'):
                dados_ar = self.sensores_dados.get('qualidade_ar', [])
                if dados_ar:
                    ultimo = dados_ar[-1]
                    base_status.update({
                        "tipo_sensor": "Qualidade do Ar Multi-parâmetro",
                        "co2": f"{ultimo['co2']:.1f} ppm",
                        "pm25": f"{ultimo['pm25']:.1f} µg/m³",
                        "pm10": f"{ultimo['pm10']:.1f} µg/m³",
                        "qualidade_geral": ultimo['qualidade'],
                        "nivel_risco": ultimo.get('nivel_risco', 'Baixo'),
                        "umidade": f"{45 + (hash(device_id) % 30)}%",
                        "temperatura_ambiente": f"{18 + (hash(device_id) % 10)}°C",
                        "pressao_atmosferica": f"{1013 + (hash(device_id) % 20)} hPa",
                        "indice_qualidade": {
                            "AQI": hash(device_id) % 150,
                            "categoria": ultimo['qualidade'],
                            "recomendacao": self._get_recomendacao_ar(ultimo['qualidade'])
                        },
                        "calibracao": {
                            "co2": "2025-04-10",
                            "particulas": "2025-04-10", 
                            "proxima": "2025-10-10"
                        },
                        "especificacoes": {
                            "co2_range": "0-5000 ppm",
                            "pm25_range": "0-500 µg/m³",
                            "precisao_co2": "±30 ppm",
                            "precisao_pm": "±10%"
                        }
                    })
        
        return base_status
    
    def _get_recomendacao_ar(self, qualidade):
        """Retorna recomendação baseada na qualidade do ar"""
        recomendacoes = {
            'EXCELENTE': 'Qualidade do ar ideal. Atividades ao ar livre recomendadas.',
            'BOA': 'Qualidade do ar aceitável. Atividades normais podem ser realizadas.',
            'MODERADA': 'Pessoas sensíveis devem considerar reduzir atividades prolongadas ao ar livre.',
            'RUIM': 'Todos devem reduzir atividades ao ar livre. Pessoas sensíveis devem evitar.',
            'PÉSSIMA': 'Emergência de saúde. Todos devem evitar atividades ao ar livre.'
        }
        return recomendacoes.get(qualidade, 'Dados insuficientes para recomendação.')
    
    def camera_ligar_grpc(self, device_id):
        print(f"📹 Ligando câmera {device_id} via gRPC")
        try:
            device_info = self.dispositivos_conectados.get(device_id)
            if not device_info:
                return "Device not found"
            
            endereco = device_info['endereco']
            with grpc.insecure_channel(endereco) as channel:
                stub = smart_city_pb2_grpc.CameraStub(channel)
                request = smart_city_pb2.Vazio()
                response = stub.Ligar(request)
                print(f"✅ Câmera {device_id} ligada com sucesso")
                return "Camera ligada"
        except Exception as e:
            print(f"❌ Erro ao ligar câmera {device_id}: {e}")
            return f"Erro: {e}"
    
    def camera_desligar_grpc(self, device_id):
        print(f"📹 Desligando câmera {device_id} via gRPC")
        try:
            device_info = self.dispositivos_conectados.get(device_id)
            if not device_info:
                return "Device not found"
            
            endereco = device_info['endereco']
            with grpc.insecure_channel(endereco) as channel:
                stub = smart_city_pb2_grpc.CameraStub(channel)
                request = smart_city_pb2.Vazio()
                response = stub.Desligar(request)
                print(f"✅ Câmera {device_id} desligada com sucesso")
                return "Camera desligada"
        except Exception as e:
            print(f"❌ Erro ao desligar câmera {device_id}: {e}")
            return f"Erro: {e}"
    
    def camera_set_resolucao_grpc(self, device_id, resolucao):
        print(f"📹 Alterando resolução da câmera {device_id} para {resolucao} via gRPC")
        try:
            device_info = self.dispositivos_conectados.get(device_id)
            if not device_info:
                return "Device not found"
            
            endereco = device_info['endereco']
            with grpc.insecure_channel(endereco) as channel:
                stub = smart_city_pb2_grpc.CameraStub(channel)
                request = smart_city_pb2.ConfigCamera(resolucao=resolucao)
                response = stub.SetResolucao(request)
                print(f"✅ Resolução da câmera {device_id} alterada para {resolucao}")
                return f"Resolução alterada para {resolucao}"
        except Exception as e:
            print(f"❌ Erro ao alterar resolução da câmera {device_id}: {e}")
            return f"Erro: {e}"
    
    def camera_iniciar_gravacao_grpc(self, device_id):
        print(f"🔴 Iniciando gravação da câmera {device_id} via gRPC")
        return "Gravação iniciada"
    
    def camera_parar_gravacao_grpc(self, device_id):
        print(f"⏹️  Parando gravação da câmera {device_id} via gRPC")
        return "Gravação parada"
    
    def poste_ligar_lampada_grpc(self, device_id):
        print(f"💡 Ligando lâmpada do poste {device_id} via gRPC")
        try:
            device_info = self.dispositivos_conectados.get(device_id)
            if not device_info:
                return "Device not found"
            
            endereco = device_info['endereco']
            with grpc.insecure_channel(endereco) as channel:
                stub = smart_city_pb2_grpc.PosteStub(channel)
                request = smart_city_pb2.Vazio()
                response = stub.LigarLampada(request)
                print(f"✅ Lâmpada do poste {device_id} ligada com sucesso")
                return "Lâmpada ligada"
        except Exception as e:
            print(f"❌ Erro ao ligar lâmpada do poste {device_id}: {e}")
            return f"Erro: {e}"
    
    def poste_desligar_lampada_grpc(self, device_id):
        print(f"💡 Desligando lâmpada do poste {device_id} via gRPC")
        try:
            device_info = self.dispositivos_conectados.get(device_id)
            if not device_info:
                return "Device not found"
            
            endereco = device_info['endereco']
            with grpc.insecure_channel(endereco) as channel:
                stub = smart_city_pb2_grpc.PosteStub(channel)
                request = smart_city_pb2.Vazio()
                response = stub.DesligarLampada(request)
                print(f"✅ Lâmpada do poste {device_id} desligada com sucesso")
                return "Lâmpada desligada"
        except Exception as e:
            print(f"❌ Erro ao desligar lâmpada do poste {device_id}: {e}")
            return f"Erro: {e}"
    
    def poste_set_intensidade_grpc(self, device_id, intensidade):
        print(f"💡 Alterando intensidade do poste {device_id} para {intensidade}% via gRPC")
        try:
            device_info = self.dispositivos_conectados.get(device_id)
            if not device_info:
                return "Device not found"
            
            endereco = device_info['endereco']
            with grpc.insecure_channel(endereco) as channel:
                stub = smart_city_pb2_grpc.PosteStub(channel)
                request = smart_city_pb2.ConfigPoste(intensidade=intensidade)
                response = stub.SetIntensidade(request)
                print(f"✅ Intensidade do poste {device_id} alterada para {intensidade}%")
                return f"Intensidade alterada para {intensidade}%"
        except Exception as e:
            print(f"❌ Erro ao alterar intensidade do poste {device_id}: {e}")
            return f"Erro: {e}"
    
    def semaforo_ligar_grpc(self, device_id):
        print(f"🚦 Ligando semáforo {device_id} via gRPC")
        try:
            device_info = self.dispositivos_conectados.get(device_id)
            if not device_info:
                return "Device not found"
            
            endereco = device_info['endereco']
            with grpc.insecure_channel(endereco) as channel:
                stub = smart_city_pb2_grpc.SemaforoStub(channel)
                request = smart_city_pb2.Vazio()
                response = stub.Ligar(request)
                print(f"✅ Semáforo {device_id} ligado com sucesso")
                return "Semáforo ligado"
        except Exception as e:
            print(f"❌ Erro ao ligar semáforo {device_id}: {e}")
            return f"Erro: {e}"
    
    def semaforo_desligar_grpc(self, device_id):
        print(f"🚦 Desligando semáforo {device_id} via gRPC")
        try:
            device_info = self.dispositivos_conectados.get(device_id)
            if not device_info:
                return "Device not found"
            
            endereco = device_info['endereco']
            with grpc.insecure_channel(endereco) as channel:
                stub = smart_city_pb2_grpc.SemaforoStub(channel)
                request = smart_city_pb2.Vazio()
                response = stub.Desligar(request)
                print(f"✅ Semáforo {device_id} desligado com sucesso")
                return "Semáforo desligado"
        except Exception as e:
            print(f"❌ Erro ao desligar semáforo {device_id}: {e}")
            return f"Erro: {e}"
    
    def semaforo_modo_emergencia_grpc(self, device_id):
        print(f"🚨 Ativando modo emergência do semáforo {device_id} via gRPC")
        try:
            device_info = self.dispositivos_conectados.get(device_id)
            if not device_info:
                return "Device not found"
            
            endereco = device_info['endereco']
            with grpc.insecure_channel(endereco) as channel:
                stub = smart_city_pb2_grpc.SemaforoStub(channel)
                request = smart_city_pb2.Vazio()
                response = stub.ModoEmergencia(request)
                print(f"✅ Modo emergência do semáforo {device_id} ativado")
                return "Modo emergência ativado"
        except Exception as e:
            print(f"❌ Erro ao ativar modo emergência do semáforo {device_id}: {e}")
            return f"Erro: {e}"
    
    def semaforo_set_tempos_grpc(self, device_id, tempos):
        print(f"🚦 Alterando tempos do semáforo {device_id} via gRPC: {tempos}")
        try:
            device_info = self.dispositivos_conectados.get(device_id)
            if not device_info:
                return "Device not found"
            
            endereco = device_info['endereco']
            with grpc.insecure_channel(endereco) as channel:
                stub = smart_city_pb2_grpc.SemaforoStub(channel)
                request = smart_city_pb2.ConfigSemaforo(
                    tempo_vermelho=tempos.get('vermelho', 30),
                    tempo_verde=tempos.get('verde', 25),
                    tempo_amarelo=tempos.get('amarelo', 5)
                )
                response = stub.SetTempos(request)
                print(f"✅ Tempos do semáforo {device_id} alterados")
                return f"Tempos alterados: {tempos}"
        except Exception as e:
            print(f"❌ Erro ao alterar tempos do semáforo {device_id}: {e}")
            return f"Erro: {e}"
    
    def iniciar_gateway(self):
        """Inicia o Gateway Inteligente"""
        print("🏙️  INICIANDO GATEWAY INTELIGENTE")
        print("="*50)
        
        # 1. Conectar ao broker
        if not self.conectar_broker():
            print("❌ Falha ao conectar ao broker. Parando Gateway.")
            return
        
        # 2. Iniciar consumidores
        self.iniciar_consumidores()
        
        # 3. Descobrir dispositivos
        self.descobrir_dispositivos()
        
        # 4. Iniciar serviço web
        print(f"🌐 Iniciando serviço web na porta {self.web_port}")
        print(f"📱 Acesse: http://localhost:{self.web_port}")
        print("="*50)
        
        # Executar Flask em modo thread para permitir redescoberta periódica
        def run_flask():
            self.app.run(host='0.0.0.0', port=self.web_port, debug=False, threaded=True)
        
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        # 5. Redescoberta periódica
        try:
            while self.running:
                time.sleep(120)  # Redescobrir a cada 2 minutos para reduzir ruído
                if self.running:
                    print("🔄 Redescoberta automática...")
                    self.descobrir_dispositivos()
                
        except KeyboardInterrupt:
            print("\n🛑 Parando Gateway...")
            self.running = False
            if self.broker_connection:
                self.broker_connection.close()
            print("Gateway parado com sucesso!")

    def _health_check_loop(self):
        """Loop em background que verifica saúde dos dispositivos"""
        while self.running:
            try:
                time.sleep(self.health_check_interval)
                if self.running:
                    self._verificar_saude_dispositivos()
            except Exception as e:
                print(f"❌ Erro no health check: {e}")

    def _verificar_saude_dispositivos(self):
        """Verifica se os dispositivos ainda estão responsivos"""
        dispositivos_inativos = []
        
        print("🩺 Verificando saúde dos dispositivos...")
        
        for device_id, device_info in list(self.dispositivos_conectados.items()):
            device_type = device_info['tipo']
            
            # Sensores comunicam apenas via RabbitMQ, não precisam de verificação gRPC
            if device_type in ['SENSOR_TEMPERATURA', 'SENSOR_QUALIDADE_AR', 'SENSOR']:
                # Para sensores, verificamos se recebemos dados recentemente via RabbitMQ
                agora = datetime.now()
                ultima_leitura = None
                
                # Verificar dados de temperatura para TEMP sensors
                if (device_type == 'SENSOR_TEMPERATURA' or 
                    (device_type == 'SENSOR' and device_id.startswith('TEMP'))) and self.sensores_dados['temperatura']:
                    
                    for temp_data in reversed(self.sensores_dados['temperatura'][-10:]):  # Check last 10 readings
                        if temp_data.get('sensor_id') == device_id:
                            ultima_leitura = datetime.fromisoformat(temp_data['timestamp'])
                            break
                        
                # Verificar dados de qualidade do ar para AIR sensors      
                elif (device_type == 'SENSOR_QUALIDADE_AR' or 
                      (device_type == 'SENSOR' and device_id.startswith('AIR'))) and self.sensores_dados['qualidade_ar']:
                    
                    for ar_data in reversed(self.sensores_dados['qualidade_ar'][-10:]):  # Check last 10 readings
                        if ar_data.get('sensor_id') == device_id:
                            ultima_leitura = datetime.fromisoformat(ar_data['timestamp'])
                            break
                
                # Se não recebemos dados nos últimos 60 segundos, considerar inativo
                if ultima_leitura and (agora - ultima_leitura).total_seconds() > 60:
                    print(f"❌ SENSOR {device_id} sem dados há {int((agora - ultima_leitura).total_seconds())}s")
                    dispositivos_inativos.append(device_id)
                else:
                    if ultima_leitura:
                        segundos_atras = int((agora - ultima_leitura).total_seconds())
                        print(f"✅ SENSOR {device_id} dados recentes ({segundos_atras}s atrás)")
                    else:
                        print(f"⚠️ SENSOR {device_id} sem dados recentes, mas mantendo ativo")
                continue
            
            # Para dispositivos gRPC (câmeras, postes, semáforos)
            ip = device_info['ip']
            porta = device_info['porta_grpc']
            
            try:
                with grpc.insecure_channel(f'{ip}:{porta}', options=[
                    ('grpc.keepalive_time_ms', 5000),
                    ('grpc.keepalive_timeout_ms', 2000),
                    ('grpc.keepalive_permit_without_calls', True),
                    ('grpc.http2.max_pings_without_data', 0),
                    ('grpc.http2.min_time_between_pings_ms', 1000),
                    ('grpc.http2.min_ping_interval_without_data_ms', 5000)
                ]) as channel:
                    grpc.channel_ready_future(channel).result(timeout=self.health_check_timeout)
                    print(f"✅ {device_info['tipo']} {device_id} está ativo")
                    
            except Exception as e:
                print(f"❌ {device_info['tipo']} {device_id} não está respondendo: {e}")
                dispositivos_inativos.append(device_id)
        
        # Remove dispositivos que não respondem
        for device_id in dispositivos_inativos:
            device_info = self.dispositivos_conectados[device_id]
            print(f"🗑️ Removendo {device_info['tipo']} {device_id} (inativo)")
            del self.dispositivos_conectados[device_id]
        
        if dispositivos_inativos:
            print(f"📊 Dispositivos ativos restantes: {len(self.dispositivos_conectados)}")
        else:
            print("✅ Todos os dispositivos estão saudáveis")

if __name__ == "__main__":
    gateway = GatewayInteligente()
    gateway.iniciar_gateway()
