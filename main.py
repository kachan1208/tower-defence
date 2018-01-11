import math

from cocos import *
from cocos.director import director
from cocos.actions.interval_actions import *
from cocos.actions import Driver, CallFunc, Delay
import pyglet

from tools import primitives


BULLETS_LAYER = None


class BaseUnit(sprite.Sprite):
    image = None
    scale = None

    def __init__(self, *args, **kwargs):
        self.layer = kwargs.pop('layer', None)

        kwargs.setdefault('scale', self.scale)
        super().__init__(self.image, *args, **kwargs)
        self.scale_x = self.scale
        self.scale_y = self.scale

        x, y = director.get_window_size()
        x, y = x/2, y/2
        self.position = (x, y)

    def look_at(self, target):
        d_x = (self.x - target.x)
        d_y = (self.y - target.y)
        if not d_x:
            d_x = 1
        if not d_y:
            d_y = 1
        degrees = math.atan(d_y/d_x)
        degrees = -math.degrees(degrees) + 90
        if target.x <= self.x:
            degrees += 180
        self.rotation = degrees
        self.do(RotateTo(degrees, 0))

    def die(self):
        try:
            self.layer.remove(self)
        except:
            pass


class EnemyDriver(Driver):
    def step(self, *args, **kwargs):
        super().step(*args, **kwargs)
        director.dispatch_event('on_enemy_move', self.target)
director.register_event_type('on_enemy_move')


class Bullet(BaseUnit):
    speed = 10
    scale = 0.5
    image = 'assets/bullet1.png'

    def __init__(self, spawn_coord, enemy, speed=0.2, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.look_at(enemy)
        self.layer.add(self)
        self.do(MoveTo((enemy.x, enemy.y), speed)+CallFunc(self.die))


class TowerButton(sprite.Sprite):
    is_event_handler = True

    def __init__(self, tower_class, *args, **kwargs):
        super().__init__(tower_class.image, *args, **kwargs)
        self.scale_x = tower_class.scale
        self.scale_y = tower_class.scale

    def on_mouse_release(self, *args, **kwargs):
        print('test', flush=True)


class Tower(BaseUnit):
    attack_radius = 115
    selected_enemy = None
    is_attacking = False
    attack_delay = 0.2
    power = attack_delay*70
    scale = 0.25
    image = 'assets/tower1.png'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_enemy_move(self, enemy):
        if not self.selected_enemy and self.is_can_attack(enemy):
            self.selected_enemy = enemy
        if self.selected_enemy and self.is_can_attack(enemy):
            self.look_at(self.selected_enemy)
            if not self.is_attacking:
                self.is_attacking = True
                self.do(CallFunc(self.attack, self.selected_enemy)+Delay(self.attack_delay)+CallFunc(self.finish_attack)+CallFunc(self.check_enemy_died))

    def make_bullet(self, enemy):
        Bullet((self.x, self.y), enemy, speed=self.attack_delay, layer=BULLETS_LAYER)

    def attack(self, enemy):
        self.do(CallFunc(self.make_bullet, enemy)+Delay(self.attack_delay)+CallFunc(enemy.damage, self.power))
    
    def check_enemy_died(self):
        if self.selected_enemy.died:
            self.selected_enemy = None

    def finish_attack(self):
        self.is_attacking = False

    def is_can_attack(self, enemy):
        distance = math.sqrt(pow(enemy.x - self.x, 2) + pow(enemy.y - self.y, 2))
        return distance <= self.attack_radius

    def draw(self, *args, **kwargs):
        super().draw(*args, **kwargs)
        primitives.Circle(
            x=self.x, 
            y=self.y,
            width=self.attack_radius*2,
            color=(1, 1, 1, 0.2), 
            stroke=1
        ).render()
        

class Enemy(BaseUnit):
    max_hp = 100
    hp = max_hp
    layer = None
    speed = 50
    died = False
    scale = 0.1
    image = 'assets/enemy1.png'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        x, y = director.get_window_size()        
        x = 200
        y = 100
        self.position = (x, y)

    def start(self):
        self.driver = EnemyDriver(self)
        self.do(self.driver)

    def check_is_alive(self):
        if self.hp <= 0:
            self.died = True
            self.die()

    def damage(self, power):
        new_hp = self.hp - power
        if new_hp <= 0:
            self.hp = 0
        else:
            self.hp = new_hp

        self.check_is_alive()

    def draw(self, *args, **kwargs):
        super().draw(*args, **kwargs)

        if self.x > 0 and self.y > 0:
            x, y = self.x, self.y
            y += self.height/2
            x -= self.width/2

            size = self.width/100*(self.hp/self.max_hp*100)
            start = x, y
            end = x+size, y

            primitives.Line(start, end, color=(1, 0, 0, 1), stroke=3).render()


class MainLayer(layer.Layer):
    def __init__(self):
        super().__init__()

        tower = Tower(layer=self)
        director.push_handlers(tower)
        self.add(tower)

        for i in range(3):
            enemy = Enemy()
            self.add(enemy)
            enemy.start()
            enemy.layer = self
            enemy.x += i*30
            # if i % 2 == 0:
            #     enemy.y -= 30
            enemy.speed = 50

class TowerBar(layer.Layer):
    towers = [Tower, Tower]
    is_event_handler = True

    def __init__(self):
        super().__init__()

        x, y = 0, 0

        self.buttons = []
        for i, tower in enumerate(self.towers):
            tower_button = TowerButton(tower, anchor=(0, 0))
            if i != 0:
                x += tower_button.width
            tower_button.x = x
            tower_button.y = y
            self.add(tower_button)
            self.buttons.append(tower_button)
    
    def on_mouse_release(self, x, y, *args, **kwargs):
        for i, button in enumerate(self.buttons):
            sx, sy = button.position
            contains = True
            if (x < sx or x > sx + button.width) or (y < sy or y > sy + button.height):
                contains = False
            if contains:
                print('Clicked on tower #{}'.format(i+1), flush=True)



def main():
    global BULLETS_LAYER
    director.init(600, 600, autoscale=False)
    main_layer = MainLayer()
    BULLETS_LAYER = layer.Layer()
    tower_bar = TowerBar()
    director.run(scene.Scene(BULLETS_LAYER, main_layer, tower_bar))

if __name__ == '__main__':
    main()
