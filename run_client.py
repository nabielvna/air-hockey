# run_client.py
import pygame
import sys
import logging
from src.common.settings import WIDTH, HEIGHT, FPS, LOAD_BALANCER_PORT
from src.client.renderer import Renderer
from src.client.network import LoadBalancerClient

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Air Hockey - Client")
    clock = pygame.time.Clock()
    renderer = Renderer(screen)
    
    print("=" * 60)
    print(" " * 20, "AIR HOCKEY - CLIENT")
    print("=" * 60)
    
    default_lb_ip = "127.0.0.1"
    lb_ip = input(f"Masukkan IP Load Balancer (default: {default_lb_ip}): ").strip() or default_lb_ip
    
    port_input = input(f"Masukkan Port Load Balancer (default: {LOAD_BALANCER_PORT}): ").strip()
    lb_port = int(port_input) if port_input else LOAD_BALANCER_PORT
    
    print(f"\nMenghubungkan ke Load Balancer di {lb_ip}:{lb_port}...")

    client = LoadBalancerClient(lb_ip, lb_port)
    game_display_state = "main_menu"
    
    # Variabel untuk melacak skor dan memicu efek
    last_scores = {'1': 0, '2': 0}

    # Inisialisasi Rects untuk menu
    main_menu_start_rect, main_menu_restart_rect, main_menu_quit_rect = None, None, None
    ingame_menu_restart_rect, ingame_menu_quit_rect = None, None
    
    # DIUBAH: Variabel untuk restart request UI
    restart_yes_rect, restart_no_rect, restart_cancel_rect = None, None, None
    restart_selected = None

    client.running = True
    while client.running:
        current_game_state = client.get_state()
        connection_info = client.get_connection_info()
        mouse_pos = pygame.mouse.get_pos()

        # Logika untuk mendeteksi gol dan memicu efek
        if current_game_state and current_game_state['status'] == 'active':
            current_scores = current_game_state.get('scores', {'1': 0, '2': 0})
            if current_scores['1'] != last_scores['1'] or current_scores['2'] != last_scores['2']:
                print("Goal detected! Triggering effects.")
                renderer.trigger_goal_effect()
                last_scores = current_scores.copy()

        # DIUBAH: Cek apakah ada restart request aktif
        is_restart_request_active = False
        restart_request_info = None
        if current_game_state and current_game_state.get('restart_request', {}).get('active', False):
            is_restart_request_active = True
            restart_request_info = current_game_state['restart_request']

        # Transisi state yang lebih rapi dengan dukungan countdown dan restart request
        if game_display_state == "game_active":
            if not client.connected:
                game_display_state = "main_menu"
                client.latest_state = None
            elif current_game_state and current_game_state['status'] == 'game_over':
                game_display_state = "game_over_screen"
            elif is_restart_request_active:
                game_display_state = "restart_request"
        
        # Auto-resume jika server mengatakan player ini sudah tidak pause
        elif game_display_state == "ingame_menu":
            if is_restart_request_active:
                game_display_state = "restart_request"
            elif current_game_state and client.player_id:
                paused_players = current_game_state.get('paused_players', [])
                # Jika player ini sudah tidak ada di daftar paused_players, kembali ke game
                if client.player_id not in paused_players:
                    game_display_state = "game_active"
                    print("Auto-resumed: You are no longer in pause state")
        
        # DIUBAH: Handle transisi dari restart request
        elif game_display_state == "restart_request":
            if not is_restart_request_active:
                # Request selesai, kembali ke game
                game_display_state = "game_active"
                restart_selected = None

        # Event handling yang lebih terstruktur
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                client.running = False
            
            # DIUBAH: Handle keyboard input untuk restart request
            if event.type == pygame.KEYDOWN:
                if game_display_state == "restart_request" and restart_request_info:
                    requester = restart_request_info.get('requester')
                    responder = restart_request_info.get('responder')
                    
                    if client.player_id == responder:
                        # Player yang menerima request - bisa accept/reject
                        if event.key == pygame.K_y:
                            client.send_respond_restart(True)
                            print("Accepted restart request")
                        elif event.key == pygame.K_n:
                            client.send_respond_restart(False)
                            print("Rejected restart request")
                    elif client.player_id == requester:
                        # Player yang mengirim request - bisa cancel
                        if event.key == pygame.K_ESCAPE:
                            client.send_cancel_restart_request()
                            print("Cancelled restart request")
                
                # Handle ESC untuk pause/resume (tidak bisa jika ada restart request)
                elif event.key == pygame.K_ESCAPE:
                    if game_display_state == "game_active":
                        # Hanya bisa pause jika tidak ada countdown resume dan tidak ada restart request
                        if (current_game_state and 
                            not (current_game_state.get('countdown', 0) > 0 and 
                                 current_game_state.get('countdown_type') == 'resume') and
                            not is_restart_request_active):
                            client.send_game_command('pause_game')
                            game_display_state = "ingame_menu"
                            print("Game paused - waiting for all players to unpause")
                        elif is_restart_request_active:
                            print("Cannot pause during restart request")
                        else:
                            print("Cannot pause during resume countdown")
                    elif game_display_state == "ingame_menu":
                        # Hanya bisa resume jika player ini masih dalam pause state
                        if current_game_state and client.player_id:
                            paused_players = current_game_state.get('paused_players', [])
                            if client.player_id in paused_players:
                                client.send_game_command('resume_game')
                                print("Resume requested - game will resume when all players unpause")
                            else:
                                print("You have already resumed - waiting for other players")

            if event.type == pygame.MOUSEMOTION:
                # Update selected option based on mouse position
                if game_display_state == "restart_request":
                    restart_selected = None
                    if restart_yes_rect and restart_yes_rect.collidepoint(mouse_pos):
                        restart_selected = "yes"
                    elif restart_no_rect and restart_no_rect.collidepoint(mouse_pos):
                        restart_selected = "no"
                    elif restart_cancel_rect and restart_cancel_rect.collidepoint(mouse_pos):
                        restart_selected = "cancel"

            if event.type == pygame.MOUSEBUTTONDOWN:
                if game_display_state in ["main_menu", "game_over_screen"]:
                    # Logika klik untuk menu utama dan layar game over
                    if main_menu_start_rect and main_menu_start_rect.collidepoint(mouse_pos) and game_display_state == "main_menu":
                        if client.connect():
                            client.start_listening_thread()
                            game_display_state = "game_active"
                        else:
                            renderer.draw_connection_status(screen, client.get_connection_info())
                            pygame.display.flip()
                            pygame.time.wait(1500)
                    elif main_menu_restart_rect and main_menu_restart_rect.collidepoint(mouse_pos) and game_display_state == "game_over_screen":
                        if client.connected:
                            # DIUBAH: Request restart, bukan langsung restart
                            client.send_request_restart()
                            print("Requested restart")
                    elif main_menu_quit_rect and main_menu_quit_rect.collidepoint(mouse_pos):
                        client.running = False
                
                # Logika klik untuk menu pause
                elif game_display_state == "ingame_menu":
                    if ingame_menu_restart_rect and ingame_menu_restart_rect.collidepoint(mouse_pos):
                        # DIUBAH: Request restart, bukan langsung restart
                        client.send_request_restart()
                        print("Requested restart")
                    elif ingame_menu_quit_rect and ingame_menu_quit_rect.collidepoint(mouse_pos):
                        client.running = False
                
                # DIUBAH: Logika klik untuk restart request
                elif game_display_state == "restart_request" and restart_request_info:
                    requester = restart_request_info.get('requester')
                    responder = restart_request_info.get('responder')
                    
                    if client.player_id == responder:
                        # Player yang menerima request
                        if restart_yes_rect and restart_yes_rect.collidepoint(mouse_pos):
                            client.send_respond_restart(True)
                            print("Accepted restart request")
                        elif restart_no_rect and restart_no_rect.collidepoint(mouse_pos):
                            client.send_respond_restart(False)
                            print("Rejected restart request")
                    elif client.player_id == requester:
                        # Player yang mengirim request
                        if restart_cancel_rect and restart_cancel_rect.collidepoint(mouse_pos):
                            client.send_cancel_restart_request()
                            print("Cancelled restart request")
            
            # Paddle movement logic - hanya blokir saat pause, countdown resume, atau restart request
            if (game_display_state == "game_active" and event.type == pygame.MOUSEMOTION and 
                current_game_state):
                # DIUBAH: Izinkan movement kecuali saat pause, countdown resume, atau restart request
                is_movement_blocked = (current_game_state.get('is_paused', False) or
                                     (current_game_state.get('countdown', 0) > 0 and 
                                      current_game_state.get('countdown_type') == 'resume') or
                                     is_restart_request_active)
                if not is_movement_blocked:
                    client.send_paddle_update(pygame.mouse.get_pos())

        # Blok Rendering Utama
        screen.fill((0, 0, 0)) # Hapus layar sekali di awal

        if game_display_state == "main_menu":
            selected_option = None
            # Dapatkan rects untuk deteksi hover
            rects = renderer.draw_main_menu("main")
            if rects[0] and rects[0].collidepoint(mouse_pos): selected_option = "start"
            if rects[2] and rects[2].collidepoint(mouse_pos): selected_option = "quit"
            # Gambar ulang dengan highlight
            main_menu_start_rect, _, main_menu_quit_rect = renderer.draw_main_menu("main", selected_option)

        elif game_display_state == "game_over_screen":
            # Gambar state game yang terakhir sebagai background
            if current_game_state:
                renderer.draw(current_game_state, client.player_id, connection_info)
            
            # Gambar menu game over di atasnya
            selected_option = None
            rects = renderer.draw_main_menu("game_over")
            if rects[1] and rects[1].collidepoint(mouse_pos): selected_option = "restart"
            if rects[2] and rects[2].collidepoint(mouse_pos): selected_option = "quit"
            # Gambar ulang dengan highlight
            _, main_menu_restart_rect, main_menu_quit_rect = renderer.draw_main_menu("game_over", selected_option)

        elif game_display_state == "ingame_menu":
            # Gambar state game yang dijeda sebagai background (FROZEN STATE)
            if client.connected and current_game_state:
                renderer.draw(current_game_state, client.player_id, connection_info)
            
            # Tentukan apakah player ini masih dalam status pause
            is_player_paused = False
            if current_game_state and client.player_id:
                paused_players = current_game_state.get('paused_players', [])
                is_player_paused = client.player_id in paused_players
            
            # Gambar menu pause di atasnya
            selected_option = None
            rects = renderer.draw_ingame_menu()
            if rects[0] and rects[0].collidepoint(mouse_pos): selected_option = "restart"
            if rects[1] and rects[1].collidepoint(mouse_pos): selected_option = "quit"
            # Gambar ulang dengan highlight dan status pause
            ingame_menu_restart_rect, ingame_menu_quit_rect = renderer.draw_ingame_menu(selected_option, is_player_paused)

        # DIUBAH: Render untuk restart request
        elif game_display_state == "restart_request":
            # Gambar state game sebagai background
            if client.connected and current_game_state:
                renderer.draw(current_game_state, client.player_id, connection_info)
            
            # Gambar UI restart request di atasnya
            if restart_request_info:
                rects = renderer.draw_restart_request_ui(restart_request_info, client.player_id, restart_selected)
                if rects:
                    restart_yes_rect, restart_no_rect, restart_cancel_rect = rects
                else:
                    restart_yes_rect, restart_no_rect, restart_cancel_rect = None, None, None

        elif game_display_state == "game_active":
            if client.connected and current_game_state:
                renderer.draw(current_game_state, client.player_id, connection_info)
            else:
                # Menunggu state atau menampilkan status koneksi
                renderer.draw(None, None, connection_info)
        
        # Panggil flip sekali di akhir loop untuk menampilkan semua yang sudah digambar
        pygame.display.flip()
        clock.tick(FPS)
    
    client.close()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()