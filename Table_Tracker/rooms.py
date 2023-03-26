
import secrets


class RoomRegistry :

    def __init__(self):
        self.tables = {}


    def add_user_to_room(self, room_id: str, username: str):
        self.tables[room_id].append(username)
        

    def __generate_room_id(self) -> str:
        while True:
            new_id: str = secrets.token_urlsafe(10)
            if new_id not in self.tables.keys():
                return new_id


    def add_room(self) -> str:
        room_id = self.__generate_room_id()
        self.tables[room_id] = []
        return room_id


    def remove_user_from_room(self, room_id: str, username: str):
        self.tables[room_id].remove(username)


    def remove_room(self, room_id: str):
        del self.tables[room_id]

    
    def room_exists(self, room_id: str) -> bool:
        if room_id in self.tables.keys():
            return True
        return False


    def user_in_room(self, room_id: str, username: str) -> bool:
        try:
            username in self.tables[room_id]
        except:
            return False
        else:
            return True

