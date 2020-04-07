"""
referred to https://github.com/xnx/collision for inplementation of elastic collision
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib import animation
from matplotlib.gridspec import GridSpec
from itertools import combinations
from matplotlib import colors as mcolors

colors = dict(mcolors.BASE_COLORS, **mcolors.CSS4_COLORS)
class Particle:
            
    def __init__(self, x, y, vx, vy, radius=0.01, prop=0):
        """
        Initialize the particle's position, velocity, radius, and initial property.
        """

        self.r = np.array((x, y))
        self.v = np.array((vx, vy))
        self.radius = radius
        self.mass = self.radius**2
        self.prop = prop # 0: healthy, 1: infected, 2: recovered, 3: dead
        self.prop_dict = {0: 'silver', 1: 'indianred' , 2: 'cadetblue', 3: 'dimgray'}
        self.styles = {'facecolor': self.prop_dict[self.prop]}
        self.timer = 0

    # For convenience, map the components of the particle's position and
    # velocity vector onto the attributes x, y, vx and vy.
    @property
    def x(self):
        return self.r[0]
    @x.setter
    def x(self, value):
        self.r[0] = value
    @property
    def y(self):
        return self.r[1]
    @y.setter
    def y(self, value):
        self.r[1] = value
    @property
    def vx(self):
        return self.v[0]
    @vx.setter
    def vx(self, value):
        self.v[0] = value
    @property
    def vy(self):
        return self.v[1]
    @vy.setter
    def vy(self, value):
        self.v[1] = value

    def overlaps(self, other):
        """Does the circle of this Particle overlap that of other?"""

        return np.hypot(*(self.r - other.r)) < self.radius + other.radius

    def draw(self, ax):
        """Add this Particle's Circle patch to the Matplotlib Axes ax."""

        circle = Circle(xy=self.r, radius=self.radius, **self.styles)
        ax.add_patch(circle)
        return circle
    
    def advance(self, dt):
        """Advance the Particle's position forward in time by dt."""

        self.r += self.v * dt

class Simulation:
    """
    A class for a simple infectous disease spreading simulation.
    The simulation is carried out on a square domain: 0 <= x < 1, 0 <= y < 1.
    """

    ParticleClass = Particle

    def __init__(self, n, radius=0.012, prop=0, transmission_rate=0.8, disease_duration=120, death_rate=0.2, dt=0.036, dttype=None):
        """
        Initialize the simulation with
            n Particles with radii radius,
            disease transmission rate, diseae duration, and death rate,
            particle activity level by dt.
        """

        self.init_particles(n, radius, prop)
        self.dt = dt
        self.dttype = dttype
        self.transmission_rate = transmission_rate
        self.disease_duration = disease_duration
        self.death_rate = death_rate
        
        self.nparticles = n
        self.healthy = np.array(1.)
        self.infected = np.array(0.)
        self.recovered = np.array(0.)
        self.dead = np.array(0.)
        self.comb = {}

    def place_particle(self, rad, prop):
        # Choose x, y so that the Particle is entirely inside the
        # domain of the simulation.
        x, y = rad + (1 - 2*rad) * np.random.random(2)
        # Choose a random velocity (within some reasonable range of
        # values) for the Particle.
        vr = 0.1 * np.sqrt(np.random.random()) + 0.05
        vphi = 2*np.pi * np.random.random()
        vx, vy = vr * np.cos(vphi), vr * np.sin(vphi)
        particle = self.ParticleClass(x, y, vx, vy, rad, prop)
        # Check that the Particle doesn't overlap one that's already
        # been placed.
        for p2 in self.particles:
            if p2.overlaps(particle):
                break
        else:
            self.particles.append(particle)
            return True
        return False

    def init_particles(self, n, radius, prop):
        """
        Initialize the n Particles of the simulation.
        Positions and velocities are chosen randomly; radius can be a single
        value or a sequence with n values.
        """

        try:
            iterator = iter(radius)
            assert n == len(radius)
        except TypeError:
            # r isn't iterable: turn it into a generator that returns the
            # same value n times.
            def r_gen(n, radius):
                for i in range(n):
                    yield radius
            radius = r_gen(n, radius)

        self.n = n
        self.particles = []
        for i, rad in enumerate(radius):
            # Set first 3 particles' property as 1 (infected).
            if i < 3:
                self.place_particle(rad, prop=1)
            else:
                # Try to find a random initial position for this particle.
                # Set the other particles' property as 0 (healthy).
                while not self.place_particle(rad, prop):
                    pass

    def change_velocities(self, p1, p2):
        """
        Particles p1 and p2 have collided elastically: update their
        velocities.
        """
        
        m1, m2 = p1.mass, p2.mass
        M = m1 + m2
        r1, r2 = p1.r, p2.r
        d = np.linalg.norm(r1 - r2)**2
        v1, v2 = p1.v, p2.v
        if p1.vx*p1.vy*p2.vx*p2.vy != 0:
            u1 = v1 - 2*m2 / M * np.dot(v1-v2, r1-r2) / d * (r1 - r2)
            u2 = v2 - 2*m1 / M * np.dot(v2-v1, r2-r1) / d * (r2 - r1)
            p1.v = u1
            p2.v = u2
        else:
            pass
            
    def handle_collisions(self, time):
        """
        Detect and handle any collisions between the Particles.
        When two Particles collide, they do so elastically: their velocities
        change such that both energy and momentum are conserved.
        """ 

        # We're going to need a sequence of all of the pairs of particles when
        # we are detecting collisions. combinations generates pairs of indexes
        # into the self.particles list of Particles on the fly.
        comb = []
        pairs = combinations(range(self.n), 2)
        
        # Set patience for handling collision as 2 if time (frame idx) >= 2.
        if time == 0:
            for i,j in pairs:
                if self.particles[i].overlaps(self.particles[j]):
                    self.change_velocities(self.particles[i], self.particles[j])
                    comb.append((i, j))
                    
                    props = [0, 1]
                    if self.particles[i].prop==1 and self.particles[j].prop==0:
                        self.particles[j].prop = np.random.choice(props, p=[1-self.transmission_rate, self.transmission_rate])
                        self.circles[j].set_color(self.particles[j].prop_dict[self.particles[j].prop])
                    elif self.particles[i].prop==0 and self.particles[j].prop==1:
                        self.particles[i].prop = np.random.choice(props, p=[1-self.transmission_rate, self.transmission_rate])
                        self.circles[i].set_color(self.particles[i].prop_dict[self.particles[i].prop])
        elif time == 1:
            for i,j in pairs:
                if self.particles[i].overlaps(self.particles[j]):
                    comb.append((i, j))
                    if (i, j) not in self.comb[time-1]:
                        self.change_velocities(self.particles[i], self.particles[j])
                        
                        props = [0, 1]
                        if self.particles[i].prop==1 and self.particles[j].prop==0:
                            self.particles[j].prop = np.random.choice(props, p=[1-self.transmission_rate, self.transmission_rate])
                            self.circles[j].set_color(self.particles[j].prop_dict[self.particles[j].prop])
                        elif self.particles[i].prop==0 and self.particles[j].prop==1:
                            self.particles[i].prop = np.random.choice(props, p=[1-self.transmission_rate, self.transmission_rate])
                            self.circles[i].set_color(self.particles[i].prop_dict[self.particles[i].prop])
        else:
            for i,j in pairs:
                if self.particles[i].overlaps(self.particles[j]):
                    comb.append((i, j))
                    if ((i, j) not in self.comb[time-1]) and ((i, j) not in self.comb[time-2]):
                        self.change_velocities(self.particles[i], self.particles[j])
                        
                        props = [0, 1]
                        if self.particles[i].prop==1 and self.particles[j].prop==0:
                            self.particles[j].prop = np.random.choice(props, p=[1-self.transmission_rate, self.transmission_rate])
                            self.circles[j].set_color(self.particles[j].prop_dict[self.particles[j].prop])
                        elif self.particles[i].prop==0 and self.particles[j].prop==1:
                            self.particles[i].prop = np.random.choice(props, p=[1-self.transmission_rate, self.transmission_rate])
                            self.circles[i].set_color(self.particles[i].prop_dict[self.particles[i].prop])
        
        self.comb[time] = comb

    def handle_boundary_collisions(self, p):
        """Bounce the particles off the walls elastically."""

        if p.x - p.radius < 0:
            p.x = p.radius
            p.vx = -p.vx
        if p.x + p.radius > 1:
            p.x = 1-p.radius
            p.vx = -p.vx
        if p.y - p.radius < 0:
            p.y = p.radius
            p.vy = -p.vy
        if p.y + p.radius > 1:
            p.y = 1-p.radius
            p.vy = -p.vy

    def advance_animation(self, time):
        """Advance the animation by dt, returning the updated Circles list."""

        for i, p in enumerate(self.particles):
            p.advance(self.dt)
            self.handle_boundary_collisions(p)
            self.circles[i].center = p.r
        self.handle_collisions(time)
        return self.circles

    def init(self):
        """Initialize the Matplotlib animation."""

        # Initialize particles
        self.circles = []
        for particle in self.particles:
            self.circles.append(particle.draw(self.ax1))
        
        # initialize texts
        self.texts = []
        self.texts.append(self.ax2.text(0.25,0.725, 'healthy', ha="left", va="center", fontsize=14, color='black'))
        self.texts.append(self.ax2.text(0.75,0.725, '', ha="right", va="center", fontsize=14, color='silver'))
        self.texts.append(self.ax2.text(0.25,0.575, 'infected', ha="left", va="center", fontsize=14, color='black'))
        self.texts.append(self.ax2.text(0.75,0.575, '', ha="right", va="center", fontsize=14, color='indianred'))
        self.texts.append(self.ax2.text(0.25,0.425, 'recovered', ha="left", va="center", fontsize=14, color='black'))
        self.texts.append(self.ax2.text(0.75,0.425, '', ha="right", va="center", fontsize=14, color='cadetblue'))
        self.texts.append(self.ax2.text(0.25,0.275, 'dead', ha="left", va="center", fontsize=14, color='black'))
        self.texts.append(self.ax2.text(0.75,0.275, '', ha="right", va="center", fontsize=14, color='dimgray'))
        
        # Initialize bars
        self.bar = self.ax3.bar([], [], width=1)
    
        return self.circles + self.texts + list(self.bar)

    def animate(self, i):
        """
        The function passed to Matplotlib's FuncAnimation routine.
        dttype can be one of followings: None, stop_short, stop_mid, stop_long, lightswitch.
        """
        
        if self.dttype == 'stop_short': # duration of shelter-in-place: 200
            if i >= 200:
                self.dt = 0.036 # 0.25

        elif self.dttype == 'stop_mid': # duration of shelter-in-place: 300
            if i >= 300:
                self.dt = 0.036 # 0.25

        elif self.dttype == 'stop_long': # duration of shelter-in-place: 400
            if i >= 400:
                self.dt = 0.036 # 0.25

        elif self.dttype == 'lightswitch': # duration of shelter-in-place: 320
            if i >= 80 and i < 120:
                self.dt = 0.036 # or 0.25
            elif i >= 120 and i < 200:
                self.dt = 0.015
            elif i >= 200 and i < 240:
                self.dt = 0.036 # or 0.25
            elif i >= 240 and i < 320:
                self.dt = 0.015
            elif i >= 320 and i < 360:
                self.dt = 0.036 # or 0.25
            elif i >= 360 and i < 440:
                self.dt = 0.015
            elif i >= 440:
                self.dt = 0.036

        # elif self.dttype == 'lightswitch4_21': # duration of shelter-in-place: 400
        #     if i >= 200 and i < 300:
        #         self.dt = 0.025 # or 0.36
        #     elif i >= 300 and i < 500:
        #         self.dt = 0.015
        #     elif i >= 500:
        #         self.dt = 0.036

        # elif self.dttype == 'lightswitch6_21': # duration of shelter-in-place: 480
        #     if i >= 160 and i < 240:
        #         self.dt = 0.025 # or 0.36
        #     elif i >= 240 and i < 400:
        #         self.dt = 0.015
        #     elif i >= 400 and i < 480:
        #         self.dt = 0.025 # or 0.36
        #     elif i >= 480 and i < 640:
        #         self.dt = 0.015
        #     elif i >= 640:
        #         self.dt = 0.036

        # elif self.dttype == 'lightswitch6_21_frequent': # duration of shelter-in-place: 240
        #     if i >= 80 and i < 120:
        #         self.dt = 0.025 # or 0.36
        #     elif i >= 120 and i < 200:
        #         self.dt = 0.015
        #     elif i >= 200 and i < 240:
        #         self.dt = 0.025 # or 0.36
        #     elif i >= 240 and i < 320:
        #         self.dt = 0.015
        #     elif i >= 320:
        #         self.dt = 0.036
                
        self.advance_animation(i)
        healthy = 0
        infected = 0
        recovered = 0
        dead = 0
        for idx in range(len(self.circles)):
            if self.particles[idx].prop == 1:
                self.particles[idx].timer += 1
            if (self.particles[idx].prop == 1 and self.particles[idx].timer > self.disease_duration):
                props = [2, 3]
                self.particles[idx].prop = np.random.choice(props, p=[1-self.death_rate, self.death_rate])
                self.circles[idx].set_color(self.particles[idx].prop_dict[self.particles[idx].prop])
            if self.particles[idx].prop == 3:
                self.particles[idx].x, self.particles[idx].y = 10 + 10 * np.random.random(2)
                self.particles[idx].vx, self.particles[idx].vy = (0, 0)
                self.circles[idx].center = self.particles[idx].r
            if self.particles[idx].prop == 0:
                healthy += 1
            elif self.particles[idx].prop == 1:
                infected += 1
            elif self.particles[idx].prop == 2:
                recovered += 1
            elif self.particles[idx].prop == 3:
                dead += 1
        
        self.healthy = np.append(self.healthy, healthy/self.nparticles)
        self.infected = np.append(self.infected, infected/self.nparticles)
        self.recovered = np.append(self.recovered, recovered/self.nparticles)
        self.dead = np.append(self.dead, dead/self.nparticles)

        self.texts[1].set_text(str(healthy))
        self.texts[3].set_text(str(infected))
        self.texts[5].set_text(str(recovered))
        self.texts[7].set_text(str(dead))
        
        self.ax3.clear()
        self.ax3.set_xlim(0, self.nframes)
        self.ax3.set_ylim(0, 1)
        self.ax3.xaxis.set_ticks([])
        self.ax3.yaxis.set_ticks([])
        self.bar = self.ax3.bar([*range(len(self.healthy))], self.infected, width=1, color = colors['indianred'])
        self.bar = self.ax3.bar([*range(len(self.healthy))], self.healthy, width=1, bottom=self.infected, color = colors['silver'])
        self.bar = self.ax3.bar([*range(len(self.healthy))], self.recovered, width=1, bottom=self.infected+self.healthy, color = colors['cadetblue'])
        self.bar = self.ax3.bar([*range(len(self.healthy))], self.dead, width=1, bottom=self.infected+self.healthy+self.recovered, color = colors['dimgray'])
        
        return self.circles + self.texts + list(self.bar)

    def setup_animation(self):

        # Initialize fig and axes
        self.fig = plt.figure(figsize=(10, 5))
        gs = GridSpec(2, 2, figure=self.fig)
        self.ax1 = self.fig.add_subplot(gs[:, 0])
        self.ax2 = self.fig.add_subplot(gs[0, 1])
        self.ax3 = self.fig.add_subplot(gs[1, 1])
        
        # Initialize ax1 for particles
        for s in ['top','bottom','left','right']:
            self.ax1.spines[s].set_linewidth(1)
        self.ax1.set_xlim(0, 1)
        self.ax1.set_ylim(0, 1)
        self.ax1.xaxis.set_ticks([])
        self.ax1.yaxis.set_ticks([])
        
        # Initialize ax2 for texts
        self.ax2.axis("off")
        
        # Initialize ax3 for bars
        self.ax3.spines['right'].set_visible(False)
        self.ax3.spines['top'].set_visible(False)
        self.ax3.set_xlim(0, self.nframes)
        self.ax3.set_ylim(0, 1)
        self.ax3.xaxis.set_ticks([])
        self.ax3.yaxis.set_ticks([])
        
    def save_or_show_animation(self, anim, save, filename='flattencurve.gif'):
        if save:
            if filename[-3:] == 'gif':
                # GIF
                Writer = animation.ImageMagickFileWriter(fps=60)
                anim.save(filename, writer=Writer)
            elif filename[-3:] == 'mp4':
            # MP4
                Writer = animation.FFMpegFileWriter(fps=60)
                anim.save(filename, writer=Writer)  
            
        else:
            plt.show() 

    def do_animation(self, save=False, nframes=900, interval=1000/60, filename='flattencurve.gif'):
        """
        Set up and carry out the animation.
        To save the animation as a GIF or MP4 movie, set save=True and specify filename.
        """

        self.nframes = nframes
        self.setup_animation()
        anim = animation.FuncAnimation(self.fig, self.animate,
                init_func=self.init, frames=nframes, interval=interval, blit=False)
        self.save_or_show_animation(anim, save, filename)
        
        return anim

if __name__ == '__main__':
    nparticles = 180
    radii = 0.012
    prop = 0
    nframes = 900
    transmission_rate = 0.8
    disease_duration = 120
    death_rate = 0.2
    dt = 0.015 # 0.036, 0.025
    dttype = 'lightswitch' # None, stop_short, stop_mid, stop_long, lightswitch
    
    sim = Simulation(nparticles, radii, prop, transmission_rate, disease_duration, death_rate, dt, dttype)
    sim.do_animation(save=True, nframes=nframes, filename='flattenthecurve.gif')