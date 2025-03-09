##########
# Import #
##########

import random
import util

from capture_agents import CaptureAgent
from game import Directions
from soupsieve import closest
from util import nearest_point


#################
# Team creation #
#################

# verander niet

def create_team(first_index, second_index, is_red,
                first='OffensiveReflexAgent', second='DefensiveReflexAgent', num_training=0):
    """
    This function should return a list of two agents that will form the
    team, initialized using firstIndex and secondIndex as their agent
    index numbers.  isRed is True if the red team is being created, and
    will be False if the blue team is being created.

    As a potentially helpful development aid, this function can take
    additional string-valued keyword arguments ("first" and "second" are
    such arguments in the case of this function), which will come from
    the --redOpts and --blueOpts command-line arguments to capture.py.
    For the nightly contest, however, your team will be created without
    any extra arguments, so you should make sure that the default
    behavior is what you want for the nightly contest.
    """
    return [eval(first)(first_index), eval(second)(second_index)]


###############
# Base Agent #
###############

# deze is de basis agent die we zullen gebruiken om de aanvaller en verdediger te implementeren
# => niet veranderen (???)

class ReflexCaptureAgent(CaptureAgent):
    """
    A base class for reflex agents that choose score-maximizing actions
    """

    def __init__(self, index, time_for_computing=.1):
        super().__init__(index, time_for_computing)
        self.start = None

    def register_initial_state(self, game_state):
        self.start = game_state.get_agent_position(self.index)
        CaptureAgent.register_initial_state(self, game_state)

    def choose_action(self, game_state):
        """
        Picks among the actions with the highest Q(s,a).
        """
        actions = game_state.get_legal_actions(self.index)

        # You can profile your evaluation time by uncommenting these lines
        # start = time.time()
        values = [self.evaluate(game_state, a) for a in actions]
        # print 'eval time for agent %d: %.4f' % (self.index, time.time() - start)

        max_value = max(values)
        best_actions = [a for a, v in zip(actions, values) if v == max_value]

        food_left = len(self.get_food(game_state).as_list())

        if food_left <= 2:
            best_dist = 9999
            best_action = None
            for action in actions:
                successor = self.get_successor(game_state, action)
                pos2 = successor.get_agent_position(self.index)
                dist = self.get_maze_distance(self.start, pos2)
                if dist < best_dist:
                    best_action = action
                    best_dist = dist
            return best_action

        return random.choice(best_actions)

    def get_successor(self, game_state, action):
        """
        Finds the next successor which is a grid position (location tuple).
        """
        successor = game_state.generate_successor(self.index, action)
        pos = successor.get_agent_state(self.index).get_position()
        if pos != nearest_point(pos):
            # Only half a grid position was covered
            return successor.generate_successor(self.index, action)
        else:
            return successor

    def evaluate(self, game_state, action):
        """
        Computes a linear combination of features and feature weights
        """
        features = self.get_features(game_state, action)
        weights = self.get_weights(game_state, action)
        return features * weights

    def get_features(self, game_state, action):
        """
        Returns a counter of features for the state
        """
        features = util.Counter()
        successor = self.get_successor(game_state, action)
        features['successor_score'] = self.get_score(successor)
        return features

    def get_weights(self, game_state, action):
        """
        Normally, weights do not depend on the game state.  They can be either
        a counter or a dictionary.
        """
        return {'successor_score': 1.0}


###################
# Offensive Agent #
###################

# deze agent gaat aanvallen

class OffensiveReflexAgent(ReflexCaptureAgent):
    """
  A reflex agent that seeks food. This is an agent
  we give you to get an idea of what an offensive agent might look like,
  but it is by no means the best or only way to build an offensive agent.
  """
    def __init__(self, index):
        super().__init__(index)
        self.food_collected = 0  # Houdt bij hoeveel voedsel is verzameld: handig om hem te laten spelen
        self.previous_score = 0 # We houden dit bij om te zien als score verhoogd werd of niet
        self.return_to_base = False # hij moet terug naar base als de flag op true staat

    # hier gaan we berekeningen doen
    def get_features(self, game_state, action):
        features = util.Counter()
        successor = self.get_successor(game_state, action)
        food_list = self.get_food(successor).as_list()
        my_pos = successor.get_agent_state(self.index).get_position()
        features['successor_score'] = -len(food_list)  # self.get_score(successor)

        # Compute distance to the nearest food
        if len(food_list) > 0:  # This should always be True,  but better safe than sorry
            min_distance = min([self.get_maze_distance(my_pos, food) for food in food_list])
            features['distance_to_food'] = min_distance

        # als hij voedsel opeet => teller moet naar omhoog
        #if my_pos in food_list:
         #   self.food_collected += 1

        return features

   # hier gaan we een keuze maken
    def choose_action(self, game_state):
        # 0. Variabelen die we nodig zullen hebben
        actions = game_state.get_legal_actions(self.index)
        current_position = game_state.get_agent_position(self.index)
        current_score = self.get_score(game_state)

        # 1. Identificeer vijanden + ontsnappen aan vijand (ghost) => list comphrension gebruikt: https://www.w3schools.com/python/python_lists_comprehension.asp
        enemy_indices = self.get_opponents(game_state) # capture_agents.py: lijn 221 => identificatie van onze vijanden
        dangerous_enemies = []  # dangerous enemies zijn enkel ghost enemies en niet pacman enemies
        dangerous_enemy_distance_treshold = 5  # als hij binnen 5 stappen dichtbij is => ontsnappen
        # enemy_positions = [game_state.get_agent_position(index) for index in enemy_indices] # capture.py: lijn 131 => positie van onze vijanden

        for index in enemy_indices:
            enemy_state = game_state.get_agent_state(index) # capture.py: lijn 128 => kan spook of pacman zijn
            if enemy_state.is_pacman == False: # ik heb dat zien gebruiken bij lijn 486 in capture.py => hij mag geen pacman zijn: we moeten enkel spoken ontsnappen
                enemy_position = game_state.get_agent_position(index) # haal positie op van die spook
                # Voeg de vijand toe als het binnen de gevarenafstand valt
                if enemy_position and self.get_maze_distance(enemy_position, current_position) < dangerous_enemy_distance_treshold: # capture_agents.py: lijn 252 => distance between two points: gaat "position" bevatten
                    dangerous_enemies.append(enemy_position)

        if dangerous_enemies: # zijn er dangerous enemies?
            # Kies de actie die het verst van de vijand wegleidt
            safe_actions = []
            max_safe_distance = 0 # in het begin is dit gewoon 0, maar we gaan dat wel veranderen.

            for action in actions:
                successor = self.get_successor(game_state, action)
                next_position = successor.get_agent_position(self.index)

                # De minimale afstand berekenen tot de vijand voor de huidige actie
                min_distance_to_enemy = min([self.get_maze_distance(next_position, dangerous_enemy) for dangerous_enemy in dangerous_enemies])

                # We kiezen voor de grootste afstand tot de vijand
                if min_distance_to_enemy > max_safe_distance:
                    max_safe_distance = min_distance_to_enemy # deze wordt de nieuwe veilige afstand
                    safe_actions = [action] # Deze is de enige veilige actie
                elif min_distance_to_enemy == max_safe_distance:
                    safe_actions.append(action) # Deze is een veilige actie, die we toevoegen aan andere veilige acties

            if safe_actions:
                return random.choice(safe_actions)  # Kies een willekeurige veilige actie
            else:
                return random.choice(actions) # Fallback: hij beweegde soms niet meer

        # 2. Dichtstbijzijnde voedselbron zoeken door afstanden te vergelijken
        food_collected_treshold = 2  # (er zijn 20 voedselbronnen) => als hij meer dan 2 voedselbron heeft opgegeten willen we hem terug naar base brengen
        food_list = self.get_food(game_state).as_list()

        #print(f"- food collected: {self.food_collected}")
        if food_list and self.food_collected < food_collected_treshold and self.return_to_base == False: # we willen enkel blijven eten als hij minder dan de treshold heeft gegeten

            # 2.1: We gaan eerst de dichtstbijzijnde voedsel bron zoeken
            closest_food = None # de voedselbron die het dichtstbijzijnste is
            best_distance = float('inf')

            for food in food_list:
                distance = self.get_maze_distance(current_position, food)
                if distance < best_distance:
                 closest_food = food
                 best_distance = distance

            # 2.2: Nu willen we hem naar de dichtstbijzijnde food brengen, door de juiste actie te kiezen
            if closest_food is not None:
                best_action = None
                best_distance = float('inf') # we gaan deze variabele hergebruiken

                # Loop door alle mogelijke acties, om de beste actie te vinden
                for action in actions:
                    successor = self.get_successor(game_state, action) # kijk waar de agent terechtkomt na deze actie
                    next_position = successor.get_agent_position(self.index) # krijg de nieuwe positie van de agent in de successor state
                    distance = self.get_maze_distance(next_position, closest_food) # de distance van de volgende positie naar de dichtstbijzijnde voedselbron
                    if distance < best_distance: # als deze actie dichterbij de voedselbron brengt, wordt het voorlopig de beste actie (we moeten nog verder loopen)
                        best_action = action
                        best_distance = distance

                # Controleer of de agent in de successor state op dezelfde positie als de closest_food is => verhoog counter
                successor = self.get_successor(game_state, best_action)
                next_position = successor.get_agent_position(self.index)
                if next_position == closest_food:
                    self.food_collected += 1
                    print(f"- gegeten: {self.food_collected}")

                # Als de treshold bereikt is => keer terug naar de start positie zodat we counter kunnen verhogen
                if self.food_collected >= food_collected_treshold:
                    print(f"treshold bereikt: {self.food_collected} >= {food_collected_treshold}")
                    self.return_to_base = True

                # Retourneer beste actie
                if best_action:
                    return best_action

        # 3. Als de return_to_base flag op true staat => terug naar base
        if self.return_to_base == True:
            best_distance = float('inf')
            best_action = None

            # We berekenen afstand tot de start positie
            for action in actions:
                successor = self.get_successor(game_state, action)
                next_position = successor.get_agent_position(self.index)
                distance_to_start_position = self.get_maze_distance(self.start, next_position)
                if distance_to_start_position < best_distance:
                    best_action = action
                    best_distance = distance_to_start_position

            # We willen niet dat onze agent tot de start positie gaat: we passen een trucje
            # - als current_score > previous score => betekent dat hij zijn kant bereikt heeft
            # - het kan ook zijn dat hij voedsel bronnen heeft opgegeten maar dat hij zelf werd opgegeten => food_collected moet naar 0
            if current_score > self.previous_score or current_position == self.start:
                self.previous_score = current_score  # we updaten de previous score, zodat we goed tellen voor verdere berekeningen
                #print(f"- food collected: {self.food_collected}")
                self.food_collected = 0  # Reset de teller: zodat hij weer begint te aanvallen
                self.return_to_base = False # Hij mag nu weer beginnen eten
                print(f"- current score: {current_score}, previous score: {self.previous_score}")
                print(f"- food collected: {self.food_collected}")

            return best_action  # kies de actie die de kortste afstand naar de base heeft

        # Anders kies een actie op basis van de evaluatie van de situatie: als ik deze niet deed kreeg ik error -> Want gaf gewoon NONE terug (Exception: Illegal action None)
        values = [self.evaluate(game_state, a) for a in actions]
        max_value = max(values)
        best_actions = [a for a, v in zip(actions, values) if v == max_value]

        return random.choice(best_actions) # we gaan random eruit kiezen


    def get_weights(self, game_state, action):
        return {'successor_score': 100, 'distance_to_food': -1}

###################
# Defensive Agent #
###################

# deze agent gaat verdedigen

class DefensiveReflexAgent(ReflexCaptureAgent):
    """
    A reflex agent that keeps its side Pacman-free. Again,
    this is to give you an idea of what a defensive agent
    could be like.  It is not the best or only way to make
    such an agent.
    """

    def get_features(self, game_state, action):
        features = util.Counter()
        successor = self.get_successor(game_state, action)

        my_state = successor.get_agent_state(self.index)
        my_pos = my_state.get_position()

        # bepalen of de agent in defesive modus is
        features['on_defense'] = 1
        if my_state.is_pacman: # indien de ghost een pacman wordt dan is hij in de vijand zijn base en moet hij niet verdedigen
            features['on_defense'] = 0

        # posities van de enemy bepalen en de invaders identificeren
        enemies = [successor.get_agent_state(i) for i in self.get_opponents(successor)]#enemies overall
        invaders = [a for a in enemies if a.is_pacman and a.get_position() is not None]# een pacman is een invader indien die in onze base bevindt
        features['num_invaders'] = len(invaders)# aantal invaders

        # Checken of een invader een capsule heeft opgegeten
        scared_timer = my_state.scared_timer  # hoe lang is deze agent bang
        if len(invaders) > 0:#indien er invaders zijn
            invader_positions = [a.get_position() for a in invaders]# bepaal de posities van de invaders
            dists = [self.get_maze_distance(my_pos, pos) for pos in invader_positions]# afstand tot de invader berekenen

            if scared_timer > 0: #indien de ghost bang is moet hij weg lopen en de afstand tot de pacman maximalizeren
                features['fleeing'] = 1 #weg lopen
                features['invader_distance'] = max(dists)  # afstand maximalizeren
            else:
                # anders minimalizeer de afstand tot de invader
                features['invader_distance'] = min(dists)

        # agent straffen indien hij stopt of achteruit beweegt
        if action == Directions.STOP:
            features['stop'] = 1
        rev = Directions.REVERSE[game_state.get_agent_state(self.index).configuration.direction]
        if action == rev:
            features['reverse'] = 1
        # Straf als de agent te ver weg is van zijn startpositie
        distance_from_start = self.get_maze_distance(my_pos, self.start)
        if distance_from_start < 10:  # Stel een limiet, bijvoorbeeld 15 stappen
            features['at_start'] = 1

        return features

    def get_weights(self, game_state, action):
        return {
            'num_invaders': -1000,  # Prioritize defending
            'on_defense': 100,  # Reward staying on defense
            'invader_distance': -25,  # Chase invaders when not scared
            'fleeing': 150,  # Strongly prioritize fleeing when scared
            'stop': -100,  # Discourage stopping
            'reverse': -2, # Slightly discourage reversing
            'at_start': -15  # straf voor teruggaan naar de startpositie

        }
