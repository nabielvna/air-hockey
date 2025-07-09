import math
import random

def apply_friction(vel, friction=0.998):
    """Apply friction to velocity"""
    vel[0] *= friction
    vel[1] *= friction
    return vel

def clamp_velocity(vel, max_speed=20, min_speed=1.0):
    """Clamp velocity to min and max speeds"""
    speed = math.hypot(vel[0], vel[1])
    if speed > max_speed:
        vel[0] = (vel[0] / speed) * max_speed
        vel[1] = (vel[1] / speed) * max_speed
    elif speed < min_speed and speed > 0:
        vel[0] = (vel[0] / speed) * min_speed
        vel[1] = (vel[1] / speed) * min_speed
    return vel

def handle_paddle_collision(puck_pos, puck_vel, paddle_pos, paddle_radius, puck_radius, paddle_vel, is_player1=True):
    """Handle collision between puck and paddle"""
    dist = math.hypot(puck_pos[0] - paddle_pos[0], puck_pos[1] - paddle_pos[1])
    
    if dist < puck_radius + paddle_radius:
        if dist > 0:
            normal_x = (puck_pos[0] - paddle_pos[0]) / dist
            normal_y = (puck_pos[1] - paddle_pos[1]) / dist
        else:
            normal_x = 1 if is_player1 else -1
            normal_y = 0
        
        overlap = (puck_radius + paddle_radius) - dist
        puck_pos[0] += normal_x * overlap
        puck_pos[1] += normal_y * overlap
        
        dot_product = puck_vel[0] * normal_x + puck_vel[1] * normal_y
        
        if dot_product < 0:
            puck_vel[0] -= 2 * dot_product * normal_x
            puck_vel[1] -= 2 * dot_product * normal_y
            
            angle_variation = (random.random() - 0.5) * 0.05  
            speed = math.hypot(puck_vel[0], puck_vel[1])
            current_angle = math.atan2(puck_vel[1], puck_vel[0])
            new_angle = current_angle + angle_variation
            
            puck_vel[0] = speed * math.cos(new_angle)
            puck_vel[1] = speed * math.sin(new_angle)
            
            paddle_speed = math.hypot(paddle_vel[0], paddle_vel[1])
            momentum_factor = 0.4  
            
            puck_vel[0] += paddle_vel[0] * momentum_factor
            puck_vel[1] += paddle_vel[1] * momentum_factor
            
            base_energy_boost = 1.1
            puck_vel[0] *= base_energy_boost
            puck_vel[1] *= base_energy_boost
            
            speed_bonus = min(paddle_speed * 0.02, 0.3)  
            speed_boost = 1.0 + speed_bonus
            puck_vel[0] *= speed_boost
            puck_vel[1] *= speed_boost
    
    return puck_pos, puck_vel

def handle_wall_collision(puck_pos, puck_vel, puck_radius, height):
    """Handle collision between puck and walls"""
    if puck_pos[1] <= puck_radius:
        puck_pos[1] = puck_radius
        puck_vel[1] = abs(puck_vel[1]) * 0.95  
    elif puck_pos[1] >= height - puck_radius:
        puck_pos[1] = height - puck_radius
        puck_vel[1] = -abs(puck_vel[1]) * 0.95  
    
    return puck_pos, puck_vel