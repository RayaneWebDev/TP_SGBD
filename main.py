import argparse
import re 

class Page :
    def __init__(self, page_id, load_time):
        self.page_id = page_id
        self.load_time = load_time
        self.last_access = 0
        self.dirty = 0              # par défaut, la page n'est pas dirty lors de sa création
        self.pin_count = 1          # par défaut, la page est pinée lors de sa création

    def display(self):
        print(f"Page ID: {self.page_id}")
        print(f"Load Time: {self.load_time}")
        print(f"Last Access: {self.last_access}")
        print(f"Dirty: {self.dirty}")
        print(f"Pin Count: {self.pin_count}")
        
class FIFOPolicy :
    name = "FIFO"
    
    def on_hit(self, frames, idx):
        pass  # un hit ne change pas l'ordre d'arrivée
    
    def on_load(self, frames, idx):
        pass
    
    def choose_victim(self, frames):
        # Choisir la page avec le plus ancien temps de chargement
        victim = None
        for i,p in enumerate(frames):
          if p is not None and p.pin_count == 0:
            if victim is None or p.load_time < victim.load_time:
                victim = i
        return victim
    

class LRUPolicy :
    name = "LRU"
    
    def on_hit(self, frames, idx):
        pass   # last_access mis à jour par le manager à chaque PIN
    
    def on_load(self, frames, idx):
        pass
    
    def choose_victim(self, frames):
        # Choisir la page avec le plus ancien temps d'accès
        victim = None
        for i,p in enumerate(frames):
          if p is not None and p.pin_count == 0:
            if victim is None or p.last_access < frames[victim].last_access:
                victim = i
        return victim
    
    
class ClockPolicy :
    name = "Clock"
    def __init__(self):
        self.clock_hand = 0
        
    def on_hit(self, frames, idx):
        frames[idx].ref_bit = 1

    def on_load(self, frames, idx):
        frames[idx].ref_bit = 1

    def choose_victim(self, frames):
         # Choisir la page en utilisant l'algorithme de l'horloge
        n = len(frames)
        if not any(p is not None and p.pin_count == 0 for p in frames):
            return None  # Aucune page n'est disponible pour être remplacée
        # Au plus 2 tours : le premier peut remettre tous les bits à 0
        for _ in range(2 * n + 1):
            p = frames[self.hand]
            if p.pin_count > 0:
                self.hand = (self.hand + 1) % n      
            elif p.ref_bit == 1:
                p.ref_bit = 0                        # seconde chance
                self.hand = (self.hand + 1) % n
            else:
                return self.hand                     # victime ; l'aiguille reste dessus
        return None
    
POLICIES = {
    "fifo": FIFOPolicy,
    "lru": LRUPolicy,
    "clock": ClockPolicy
}
    
class BufferManager :
    def __init__(self, n_frames=4, policy="fifo", trace=True):
        self.n = n_frames
        self.policy = POLICIES[policy.lower()]()
        self.trace = trace
        self.reset()
 
    def reset(self):
        self.frames = [None] * self.n
        self.page_table = {}   # page_id -> indice de frame
        self.clock = 0         # horloge logique (incrémentée à chaque opération)
        self.hits = self.misses = self.errors = 0
        self.reads = self.writes = 0
        self.policy.reset()
    
    def pin(self, p):
        self.clock += 1 # incrémenter l'horloge logique à chaque opération
        if p in self.page_table:     #HIT
            idx = self.page_table[p]
            page = self.frames[idx]
            page.last_access = self.clock
            page.pin_count += 1
            self.policy.on_hit(self.frames, idx)
            self.hits += 1
            return "HIT", ""            
        # MISS
        detail = "" 
        self.misses += 1
        if None in self.frames :
            idx = self.frames.index(None)
        else :
            idx = self.policy.choose_victim(self.frames)
            if idx is None:
                self.errors += 1
                return "Erreur", "Toutes les pages sont pinées, aucune page ne peut être remplacée"
            victim = self.frames[idx]
            detail = f"Remplacement de la page {victim.page_id} par la page {p}"
            if victim.dirty:
                self.writes += 1    
                detail += f" (écriture de la page {victim.page_id} sur le disque)"
                del self.page_table[victim.page_id]
                
        # Charger la nouvelle page
        self.reads += 1
        self.misses += 1
        self.frames[idx] = Page(p, self.clock)
        self.page_table[p] = idx
        return "MISS", detail
    
    def unpin(self, p, dirty=False):
        self.clock += 1
        if p not in self.page_table:
            self.errors += 1
            return "Erreur", f"La page {p} n'est pas présente dans le buffer"
        page = self.frames[self.page_table[p]]
        if page.pin_count == 0:
            self.errors += 1
            return "Erreur", f"La page {p} n'est pas pinée"
        page.pin_count -= 1
        if dirty:
            page.dirty = True
        return "OK", f"La page {p} a été unpinée {'et marquée dirty' if dirty else ''}"


