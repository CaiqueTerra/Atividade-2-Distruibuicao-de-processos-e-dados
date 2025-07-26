import requests
import json
import os
import time
from datetime import datetime

class ClienteControle:
    def __init__(self, gateway_url="http://localhost:5000"):
        self.gateway_url = gateway_url
        self.dispositivos = {}
        
    def limpar_tela(self):
        """Limpa a tela do terminal"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def exibir_menu_principal(self):
        """Exibe o menu principal"""
        self.limpar_tela()
        print("=" * 60)
        print("🏙️  CLIENTE DE CONTROLE - CIDADE INTELIGENTE")
        print("=" * 60)
        print("1. 📋 Listar dispositivos conectados")
        print("2. 🔍 Consultar status de dispositivo específico")
        print("3. 📹 Controlar câmeras")
        print("4. 💡 Controlar postes de iluminação")
        print("5. 🚦 Controlar semáforos")
        print("6. 📊 Visualizar dados dos sensores")
        print("7. 🔄 Atualizar lista de dispositivos")
        print("8. ❌ Sair")
        print("=" * 60)
    
    def fazer_requisicao(self, endpoint, metodo='GET', dados=None):
        """Faz requisição para o Gateway"""
        try:
            url = f"{self.gateway_url}/api{endpoint}"
            
            if metodo == 'GET':
                response = requests.get(url, timeout=10)
            elif metodo == 'POST':
                response = requests.post(url, json=dados, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Erro HTTP {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.ConnectionError:
            print("❌ Erro: Não foi possível conectar ao Gateway")
            print(f"   Verifique se o Gateway está rodando em {self.gateway_url}")
            return None
        except requests.exceptions.Timeout:
            print("❌ Erro: Timeout na requisição")
            return None
        except Exception as e:
            print(f"❌ Erro inesperado: {e}")
            return None
    
    def listar_dispositivos(self):
        """Lista todos os dispositivos conectados"""
        print("\n🔍 Consultando dispositivos conectados...")
        
        data = self.fazer_requisicao('/dispositivos')
        if not data:
            return
        
        self.dispositivos = {d['id']: d for d in data.get('dispositivos', [])}
        
        if not self.dispositivos:
            print("📭 Nenhum dispositivo encontrado")
            return
        
        print(f"\n📋 Dispositivos Conectados ({data['total']}):")
        print("-" * 80)
        
        for dispositivo in data['dispositivos']:
            tipo_emoji = {
                'CAMERA': '📹',
                'POSTE': '💡',
                'SEMAFORO': '🚦',
                'SENSOR': '📊'
            }.get(dispositivo['tipo'], '📱')
            
            print(f"{tipo_emoji} {dispositivo['id']} ({dispositivo['tipo']})")
            print(f"   └─ Endereço: {dispositivo.get('endereco', 'N/A')}")
            if dispositivo.get('ip'):
                print(f"   └─ IP: {dispositivo['ip']} | Porta gRPC: {dispositivo.get('porta_grpc', 'N/A')}")
            print()
    
    def consultar_status_dispositivo(self):
        """Consulta status de dispositivo específico"""
        print("\n🔍 Consultar Status de Dispositivo")
        print("-" * 40)
        
        if not self.dispositivos:
            print("❌ Execute primeiro 'Listar dispositivos' para carregar a lista")
            return
        
        print("Dispositivos disponíveis:")
        for i, device_id in enumerate(self.dispositivos.keys(), 1):
            dispositivo = self.dispositivos[device_id]
            print(f"{i}. {device_id} ({dispositivo['tipo']})")
        
        try:
            escolha = input("\nDigite o número do dispositivo (ou 'enter' para voltar): ").strip()
            if not escolha:
                return
            
            escolha = int(escolha) - 1
            device_id = list(self.dispositivos.keys())[escolha]
            
            print(f"\n🔍 Consultando status de {device_id}...")
            data = self.fazer_requisicao(f'/dispositivos/{device_id}/status')
            
            if data:
                self._exibir_status_detalhado(device_id, data)
            
        except (ValueError, IndexError):
            print("❌ Escolha inválida")
    
    def _exibir_status_detalhado(self, device_id, data):
        """Exibe status detalhado formatado"""
        print(f"\n" + "="*60)
        print(f"📋 STATUS DETALHADO: {device_id}")
        print("="*60)
        
        # Extrair os dados do status da resposta da API
        status_data = data.get('status', {}) if 'status' in data else data
        
        # Informações básicas
        print(f"🏷️  Nome: {status_data.get('nome', 'N/A')}")
        print(f"🔧 Tipo: {status_data.get('tipo', 'N/A')}")
        print(f"🌐 Endereço: {status_data.get('endereco', 'N/A')}")
        print(f"🔌 Status: {status_data.get('status_conexao', 'N/A')}")
        print(f"⏱️  Uptime: {status_data.get('uptime', 'N/A')}")
        print(f"🔄 Última comunicação: {status_data.get('ultima_comunicacao', 'N/A')}")
        print(f"📦 Firmware: {status_data.get('versao_firmware', 'N/A')}")
        print(f"🌡️  Temp. interna: {status_data.get('temperatura_interna', 'N/A')}")
        
        tipo = status_data.get('tipo', '')
        
        # Status específico por tipo
        if tipo == 'CAMERA':
            print(f"\n📹 INFORMAÇÕES DA CÂMERA:")
            print(f"   🎬 Resolução: {status_data.get('resolucao', 'N/A')}")
            print(f"   🎭 FPS: {status_data.get('fps', 'N/A')}")
            print(f"   🔍 Zoom: {status_data.get('zoom', 'N/A')}")
            print(f"   📼 Modo gravação: {status_data.get('modo_gravacao', 'N/A')}")
            print(f"   💾 Storage: {status_data.get('espaco_storage', 'N/A')}")
            print(f"   🌙 Visão noturna: {'✅' if status_data.get('modo_visao_noturna') else '❌'}")
            print(f"   👁️  Detecção movimento: {'✅' if status_data.get('deteccao_movimento') else '❌'}")
            print(f"   📐 Ângulo de visão: {status_data.get('angulo_visao', 'N/A')}")
            print(f"   🎨 Qualidade: {status_data.get('qualidade_imagem', 'N/A')}")
            print(f"   🎞️  Codec: {status_data.get('codec_video', 'N/A')}")
            print(f"   📊 Bitrate: {status_data.get('bitrate', 'N/A')}")
            
            if 'status_leds' in status_data:
                leds = status_data['status_leds']
                print(f"   💡 LEDs:")
                print(f"      🔋 Power: {leds.get('led_power', 'N/A')}")
                print(f"      🌐 Network: {leds.get('led_network', 'N/A')}")
                print(f"      📹 Recording: {leds.get('led_recording', 'N/A')}")
        
        elif tipo == 'POSTE_ILUMINACAO':
            print(f"\n💡 INFORMAÇÕES DO POSTE:")
            print(f"   🔆 Intensidade: {status_data.get('intensidade_luz', 'N/A')}")
            print(f"   ⚙️  Modo: {status_data.get('modo_operacao', 'N/A')}")
            print(f"   ☀️  Luminosidade: {status_data.get('sensor_luminosidade', 'N/A')}")
            print(f"   ⚡ Consumo: {status_data.get('consumo_energia', 'N/A')}")
            print(f"   🌡️  Temp. LED: {status_data.get('temperatura_led', 'N/A')}")
            print(f"   ⏰ Funcionamento: {status_data.get('horas_funcionamento', 'N/A')}")
            print(f"   🔋 Vida útil: {status_data.get('vida_util_restante', 'N/A')}")
            print(f"   💡 Tipo lâmpada: {status_data.get('tipo_lampada', 'N/A')}")
            print(f"   🎨 Cor temp.: {status_data.get('cor_temperatura', 'N/A')}")
            print(f"   👁️  Sensor movimento: {'✅' if status_data.get('sensor_movimento') else '❌'}")
            
            if 'programacao' in status_data:
                prog = status_data['programacao']
                print(f"   📅 Programação:")
                print(f"      🌅 Acender: {prog.get('acender', 'N/A')}")
                print(f"      🌙 Apagar: {prog.get('apagar', 'N/A')}")
                print(f"      🌃 Modo noturno: {prog.get('modo_noturno', 'N/A')}")
        
        elif tipo == 'SEMAFORO':
            print(f"\n🚦 INFORMAÇÕES DO SEMÁFORO:")
            estado = status_data.get('estado_atual', 'N/A')
            emoji_estado = {'verde': '🟢', 'amarelo': '🟡', 'vermelho': '🔴'}.get(estado, '⚪')
            print(f"   {emoji_estado} Estado atual: {estado.upper()}")
            print(f"   ⏱️  Tempo restante: {status_data.get('tempo_restante', 'N/A')}")
            print(f"   ⚙️  Modo: {status_data.get('modo_operacao', 'N/A')}")
            print(f"   🔄 Ciclo completo: {status_data.get('ciclo_completo', 'N/A')}")
            print(f"   🚗 Veículos detectados: {status_data.get('veiculos_detectados', 'N/A')}")
            print(f"   🚶 Pedestres aguardando: {status_data.get('pedestres_aguardando', 'N/A')}")
            print(f"   🚨 Modo emergência: {'✅' if status_data.get('modo_emergencia') else '❌'}")
            print(f"   🎛️  Controle central: {'✅' if status_data.get('controle_central') else '❌'}")
            
            if 'tempos_programados' in status_data:
                tempos = status_data['tempos_programados']
                print(f"   ⏰ Tempos programados:")
                print(f"      🟢 Verde: {tempos.get('verde', 'N/A')}")
                print(f"      🟡 Amarelo: {tempos.get('amarelo', 'N/A')}")
                print(f"      🔴 Vermelho: {tempos.get('vermelho', 'N/A')}")
            
            if 'lampadas_status' in status_data:
                leds = status_data['lampadas_status']
                print(f"   💡 Status das lâmpadas:")
                print(f"      🔴 LED Vermelho: {leds.get('led_vermelho', 'N/A')}")
                print(f"      🟡 LED Amarelo: {leds.get('led_amarelo', 'N/A')}")
                print(f"      🟢 LED Verde: {leds.get('led_verde', 'N/A')}")
                print(f"      🚶 LED Pedestre: {leds.get('led_pedestre', 'N/A')}")
        
        elif tipo == 'SENSOR':
            print(f"\n🔬 INFORMAÇÕES DO SENSOR:")
            
            if device_id.startswith('TEMP'):
                print(f"   🌡️  Tipo: {status_data.get('tipo_sensor', 'N/A')}")
                print(f"   📊 Valor atual: {status_data.get('valor_atual', 'N/A')}")
                print(f"   📏 Unidade: {status_data.get('unidade', 'N/A')}")
                print(f"   🎯 Precisão: {status_data.get('precisao', 'N/A')}")
                print(f"   📐 Faixa operação: {status_data.get('faixa_operacao', 'N/A')}")
                print(f"   🔧 Calibração: {status_data.get('calibracao', 'N/A')}")
                print(f"   ⏱️  Intervalo leitura: {status_data.get('intervalo_leitura', 'N/A')}")
                print(f"   📈 Tendência: {status_data.get('tendencia', 'N/A')}")
                print(f"   📊 Leituras 24h: {status_data.get('total_leituras_24h', 'N/A')}")
                print(f"   🔽 Mín. 24h: {status_data.get('valor_minimo_24h', 'N/A')}")
                print(f"   🔼 Máx. 24h: {status_data.get('valor_maximo_24h', 'N/A')}")
                
            elif device_id.startswith('AIR'):
                print(f"   🌬️  Tipo: {status_data.get('tipo_sensor', 'N/A')}")
                print(f"   🌍 Qualidade geral: {status_data.get('qualidade_geral', 'N/A')}")
                print(f"   ⚠️  Nível risco: {status_data.get('nivel_risco', 'N/A')}")
                print(f"   💨 CO2: {status_data.get('co2', 'N/A')}")
                print(f"   🌫️  PM2.5: {status_data.get('pm25', 'N/A')}")
                print(f"   🌫️  PM10: {status_data.get('pm10', 'N/A')}")
                print(f"   💧 Umidade: {status_data.get('umidade', 'N/A')}")
                print(f"   🌡️  Temp. ambiente: {status_data.get('temperatura_ambiente', 'N/A')}")
                print(f"   🌍 Pressão atm.: {status_data.get('pressao_atmosferica', 'N/A')}")
                
                if 'indice_qualidade' in status_data:
                    indice = status_data['indice_qualidade']
                    print(f"   📊 Índice qualidade:")
                    print(f"      🔢 AQI: {indice.get('AQI', 'N/A')}")
                    print(f"      📋 Categoria: {indice.get('categoria', 'N/A')}")
                    print(f"      💡 Recomendação: {indice.get('recomendacao', 'N/A')}")
        
        print("="*60)
    
    def controlar_cameras(self):
        """Menu de controle de câmeras"""
        cameras = {k: v for k, v in self.dispositivos.items() if v['tipo'] == 'CAMERA'}
        
        if not cameras:
            print("❌ Nenhuma câmera encontrada")
            return
        
        print("\n📹 Controle de Câmeras")
        print("-" * 30)
        
        print("Câmeras disponíveis:")
        for i, (device_id, dispositivo) in enumerate(cameras.items(), 1):
            print(f"{i}. {device_id}")
        
        try:
            escolha = input("\nEscolha a câmera (número): ").strip()
            if not escolha:
                return
                
            escolha = int(escolha) - 1
            device_id = list(cameras.keys())[escolha]
            
            print(f"\nControles para {device_id}:")
            print("1. Ligar câmera")
            print("2. Desligar câmera")
            print("3. Alterar resolução para HD")
            print("4. Alterar resolução para FullHD")
            print("5. Alterar resolução para 4K")
            print("6. Iniciar gravação")
            print("7. Parar gravação")
            
            acao = input("\nEscolha a ação: ").strip()
            
            comando_map = {
                '1': ('ligar', {}),
                '2': ('desligar', {}),
                '3': ('resolucao', {'resolucao': 'HD'}),
                '4': ('resolucao', {'resolucao': 'FullHD'}),
                '5': ('resolucao', {'resolucao': '4K'}),
                '6': ('gravar', {}),
                '7': ('parar_gravacao', {})
            }
            
            if acao in comando_map:
                acao_nome, params = comando_map[acao]
                data = {'acao': acao_nome, **params}
                
                print(f"\n🔄 Executando comando '{acao_nome}' em {device_id}...")
                result = self.fazer_requisicao(f'/camera/{device_id}/controle', 'POST', data)
                
                if result:
                    print(f"✅ {result.get('resultado', 'Comando executado com sucesso')}")
            else:
                print("❌ Ação inválida")
                
        except (ValueError, IndexError):
            print("❌ Escolha inválida")
    
    def controlar_postes(self):
        """Menu de controle de postes"""
        postes = {k: v for k, v in self.dispositivos.items() if v['tipo'] == 'POSTE'}
        
        if not postes:
            print("❌ Nenhum poste encontrado")
            return
        
        print("\n💡 Controle de Postes")
        print("-" * 25)
        
        print("Postes disponíveis:")
        for i, (device_id, dispositivo) in enumerate(postes.items(), 1):
            print(f"{i}. {device_id}")
        
        try:
            escolha = input("\nEscolha o poste (número): ").strip()
            if not escolha:
                return
                
            escolha = int(escolha) - 1
            device_id = list(postes.keys())[escolha]
            
            print(f"\nControles para {device_id}:")
            print("1. Ligar lâmpada")
            print("2. Desligar lâmpada")
            print("3. Intensidade 25%")
            print("4. Intensidade 50%")
            print("5. Intensidade 75%")
            print("6. Intensidade 100%")
            print("7. Intensidade personalizada")
            
            acao = input("\nEscolha a ação: ").strip()
            
            if acao == '1':
                data = {'acao': 'ligar'}
            elif acao == '2':
                data = {'acao': 'desligar'}
            elif acao in ['3', '4', '5', '6']:
                intensidades = {'3': 25, '4': 50, '5': 75, '6': 100}
                data = {'acao': 'intensidade', 'intensidade': intensidades[acao]}
            elif acao == '7':
                try:
                    intensidade = int(input("Digite a intensidade (0-100): "))
                    if 0 <= intensidade <= 100:
                        data = {'acao': 'intensidade', 'intensidade': intensidade}
                    else:
                        print("❌ Intensidade deve estar entre 0 e 100")
                        return
                except ValueError:
                    print("❌ Intensidade inválida")
                    return
            else:
                print("❌ Ação inválida")
                return
            
            print(f"\n🔄 Executando comando '{data['acao']}' em {device_id}...")
            result = self.fazer_requisicao(f'/poste/{device_id}/controle', 'POST', data)
            
            if result:
                print(f"✅ {result.get('resultado', 'Comando executado com sucesso')}")
                
        except (ValueError, IndexError):
            print("❌ Escolha inválida")
    
    def controlar_semaforos(self):
        """Menu de controle de semáforos"""
        semaforos = {k: v for k, v in self.dispositivos.items() if v['tipo'] == 'SEMAFORO'}
        
        if not semaforos:
            print("❌ Nenhum semáforo encontrado")
            return
        
        print("\n🚦 Controle de Semáforos")
        print("-" * 30)
        
        print("Semáforos disponíveis:")
        for i, (device_id, dispositivo) in enumerate(semaforos.items(), 1):
            print(f"{i}. {device_id}")
        
        try:
            escolha = input("\nEscolha o semáforo (número): ").strip()
            if not escolha:
                return
                
            escolha = int(escolha) - 1
            device_id = list(semaforos.keys())[escolha]
            
            print(f"\nControles para {device_id}:")
            print("1. Ligar semáforo")
            print("2. Desligar semáforo")
            print("3. Modo emergência")
            print("4. Configurar tempos personalizados")
            print("5. Configuração padrão (30s-25s-5s)")
            
            acao = input("\nEscolha a ação: ").strip()
            
            if acao == '1':
                data = {'acao': 'ligar'}
            elif acao == '2':
                data = {'acao': 'desligar'}
            elif acao == '3':
                data = {'acao': 'emergencia'}
            elif acao == '4':
                try:
                    print("Configure os tempos (em segundos):")
                    vermelho = int(input("Tempo vermelho: "))
                    verde = int(input("Tempo verde: "))
                    amarelo = int(input("Tempo amarelo: "))
                    
                    data = {
                        'acao': 'tempos',
                        'tempos': {
                            'tempo_vermelho': vermelho,
                            'tempo_verde': verde,
                            'tempo_amarelo': amarelo
                        }
                    }
                except ValueError:
                    print("❌ Tempos inválidos")
                    return
            elif acao == '5':
                data = {
                    'acao': 'tempos',
                    'tempos': {
                        'tempo_vermelho': 30,
                        'tempo_verde': 25,
                        'tempo_amarelo': 5
                    }
                }
            else:
                print("❌ Ação inválida")
                return
            
            print(f"\n🔄 Executando comando '{data['acao']}' em {device_id}...")
            result = self.fazer_requisicao(f'/semaforo/{device_id}/controle', 'POST', data)
            
            if result:
                print(f"✅ {result.get('resultado', 'Comando executado com sucesso')}")
                
        except (ValueError, IndexError):
            print("❌ Escolha inválida")
    
    def visualizar_dados_sensores(self):
        """Visualiza dados dos sensores"""
        print("\n📊 Dados dos Sensores")
        print("-" * 30)
        
        data = self.fazer_requisicao('/sensores/dados')
        if not data:
            return
        
        # Temperatura
        if data.get('temperatura'):
            print("\n🌡️  SENSORES DE TEMPERATURA:")
            print("-" * 40)
            
            for i, leitura in enumerate(data['temperatura'][-5:], 1):  # Últimas 5 leituras
                timestamp = datetime.fromisoformat(leitura['timestamp']).strftime('%H:%M:%S')
                print(f"{i}. {leitura['sensor_id']}: {leitura['valor']}°C ({timestamp})")
                print(f"   Localização: {leitura.get('localizacao', 'N/A')}")
            
            # Estatísticas
            valores = [l['valor'] for l in data['temperatura']]
            if valores:
                print(f"\n📈 Estatísticas:")
                print(f"   Média: {sum(valores)/len(valores):.1f}°C")
                print(f"   Mínima: {min(valores):.1f}°C")
                print(f"   Máxima: {max(valores):.1f}°C")
        
        # Qualidade do Ar
        if data.get('qualidade_ar'):
            print("\n🌬️  SENSORES DE QUALIDADE DO AR:")
            print("-" * 40)
            
            for i, leitura in enumerate(data['qualidade_ar'][-5:], 1):  # Últimas 5 leituras
                timestamp = datetime.fromisoformat(leitura['timestamp']).strftime('%H:%M:%S')
                emoji = {"BOA": "🟢", "MODERADA": "🟡", "RUIM": "🟠", "PÉSSIMA": "🔴"}.get(leitura['qualidade'], "⚪")
                
                print(f"{i}. {leitura['sensor_id']}: {emoji} {leitura['qualidade']} ({timestamp})")
                print(f"   CO2: {leitura['co2']} ppm | PM2.5: {leitura['pm25']} µg/m³ | PM10: {leitura['pm10']} µg/m³")
                print(f"   Localização: {leitura.get('localizacao', 'N/A')}")
        
        if not data.get('temperatura') and not data.get('qualidade_ar'):
            print("📭 Nenhum dado de sensor disponível")
    
    def executar(self):
        """Loop principal do cliente"""
        while True:
            self.exibir_menu_principal()
            
            try:
                opcao = input("\nEscolha uma opção: ").strip()
                
                if opcao == '1':
                    self.listar_dispositivos()
                elif opcao == '2':
                    self.consultar_status_dispositivo()
                elif opcao == '3':
                    self.controlar_cameras()
                elif opcao == '4':
                    self.controlar_postes()
                elif opcao == '5':
                    self.controlar_semaforos()
                elif opcao == '6':
                    self.visualizar_dados_sensores()
                elif opcao == '7':
                    print("\n🔄 Atualizando lista de dispositivos...")
                    self.listar_dispositivos()
                elif opcao == '8':
                    print("\n👋 Encerrando cliente...")
                    break
                else:
                    print("\n❌ Opção inválida! Tente novamente.")
                
                if opcao != '8':
                    input("\nPressione Enter para continuar...")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Encerrando cliente...")
                break
            except Exception as e:
                print(f"\n❌ Erro inesperado: {e}")
                input("\nPressione Enter para continuar...")

def main():
    print("🏙️  CLIENTE DE CONTROLE - CIDADE INTELIGENTE")
    print("=" * 50)
    
    # Configurar URL do Gateway
    gateway_url = input("URL do Gateway (Enter para padrão http://localhost:5000): ").strip()
    if not gateway_url:
        gateway_url = "http://localhost:5000"
    
    print(f"\n🔗 Conectando ao Gateway: {gateway_url}")
    
    # Testar conexão
    try:
        response = requests.get(f"{gateway_url}/api/dispositivos", timeout=5)
        if response.status_code == 200:
            print("✅ Conexão com Gateway estabelecida!")
        else:
            print(f"⚠️  Gateway respondeu com código {response.status_code}")
    except:
        print("❌ Não foi possível conectar ao Gateway")
        print("   Verifique se o Gateway está rodando")
    
    input("\nPressione Enter para continuar...")
    
    # Iniciar cliente
    cliente = ClienteControle(gateway_url)
    cliente.executar()

if __name__ == "__main__":
    main()
