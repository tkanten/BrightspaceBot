import os
import json

COLLECTIONS = os.path.join(os.path.dirname(__file__), '', "Collections")


class ObservedList(list):
    """
    Send all changes to an observer.
    """

    def __init__(self, name, value):
        self.name = name
        list.__init__(self, value)


    def __setitem__(self, key, value):
        """
        Intercept the l[key]=value operations.
        Also covers slice assignment.
        """
        try:
            oldvalue = self.__getitem__(key)
        except KeyError:
            list.__setitem__(self, key, value)
            Database.UPDATE_LIST.add(self.name)
        else:
            list.__setitem__(self, key, value)
            Database.UPDATE_LIST.add(self.name)

    def __delitem__(self, key):
        oldvalue = list.__getitem__(self, key)
        list.__delitem__(self, key)
        Database.UPDATE_LIST.add(self.name)

    def __setslice__(self, i, j, sequence):
        oldvalue = list.__getslice__(self, i, j)
        Database.UPDATE_LIST.add(self.name)
        list.__setslice__(self, i, j, sequence)

    def __delslice__(self, i, j):
        oldvalue = list.__getitem__(self, slice(i, j))
        list.__delslice__(self, i, j)
        Database.UPDATE_LIST.add(self.name)

    def append(self, value):
        list.append(self, value)
        Database.UPDATE_LIST.add(self.name)

    def pop(self):
        oldvalue = list.pop(self)
        Database.UPDATE_LIST.add(self.name)

    def extend(self, newvalue):
        list.extend(self, newvalue)
        Database.UPDATE_LIST.add(self.name)

    def insert(self, i, element):
        list.insert(self, i, element)
        Database.UPDATE_LIST.add(self.name)

    def remove(self, element):
        index = list.index(self, element)
        list.remove(self, element)
        Database.UPDATE_LIST.add(self.name)

    def removemany(self, elements):
        if isinstance(elements, list):
            for element in elements:
                index = list.index(self, element)
                list.remove(self, element)
                Database.UPDATE_LIST.add(self.name)

    def reverse(self):
        list.reverse(self)
        Database.UPDATE_LIST.add(self.name)

    def sort(self, cmpfunc=None):
        oldlist = self[:]
        list.sort(self, cmpfunc)
        Database.UPDATE_LIST.add(self.name)


class ObservedDict(dict):
    def __init__(self, name, value):

        # start by iterating through value input, change dict inputs
        # to an ObservedDict

        self.name = name
        dict.__init__(self, value)
        # self.value = value

    def __contains__(self, item):
        return item in self

    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except Exception as e:
            return None

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        Database.UPDATE_LIST.add(self.name)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        Database.UPDATE_LIST.add(self.name)


class Database:
    UPDATE_LIST = set({})

    def __init__(self):
        self.startup_database()

    def startup_database(self):
        for collection in os.listdir(COLLECTIONS):
            collection_path = os.path.join(COLLECTIONS, collection)

            # loop through each document in a collection
            for document in os.listdir(collection_path):

                attribute_name = document.split(".")[0]
                attribute_path = os.path.join(collection_path, document)

                with open(os.path.join(collection_path, document), "r") as entry:
                    raw_data = json.load(entry)

                metadata = {'TYPE': collection,
                            'NAME': attribute_name,
                            'PATH': attribute_path
                            }
                if isinstance(raw_data, dict):
                    data = ObservedDict(attribute_name, raw_data)
                elif isinstance(raw_data, list):
                    data = ObservedList(attribute_name, raw_data)
                else:
                    data = raw_data

                self.__dict__.update({attribute_name: [data, metadata]})

    def backup_data(self):
        update_count = 0
        for attribute in Database.UPDATE_LIST:
            data = self.__dict__.get(attribute)[0]
            metadata = self.__dict__.get(attribute)[1]

            with open(metadata['PATH'], 'w') as file:
                json.dump(data, file)

            update_count += 1

        Database.UPDATE_LIST = set({})

        ## VERY BULKY WAY OF ACCOMPLISHING THIS, but as soon as backup is complete
        ## go and re-pull database from disk
        #self.startup_database()
        return update_count

    def __getitem__(self, key):
        key = str(key)
        if key in self.__dict__.keys():
            # if a tuple is inputted for a getitem [attribute, meta/metadata/all] provide further options
            return self.__dict__.get(key)[0]
        elif isinstance(key, tuple):
            # return metadata
            if key[1] == 'meta' or key[1] == 'metadata':
                return self.__dict__.get(key[0])[1]
            else:
                return self.__dict__.get(key[0])

    def __setitem__(self, key_type, value):
        if isinstance(key_type, str) or isinstance(key_type, int):
            key = str(key_type)
            # if key already exists, set type as what was given before
            if key in self.__dict__.keys():
                _type = self.__dict__.get(key)[1]['TYPE']
            else:
                _type = 'unsorted'
        elif isinstance(key_type, tuple):
            key = key_type[0]
            if key_type[1] in os.listdir(COLLECTIONS):
                _type = key_type[1]
            else:
                _type = 'unsorted'
        else:
            return False

        metadata = {'TYPE': _type,
                    'NAME': key,
                    'PATH': os.path.join(COLLECTIONS, _type, f'{key}.json')
                    }

        if isinstance(value, list):
            value = ObservedList(key, value)
        elif isinstance(value, dict):
            value = ObservedDict(key, value)

        Database.UPDATE_LIST.add(key)
        self.__dict__.update({key: [value, metadata]})

    def __delitem__(self, key):
        key = str(key)
        if key in self.__dict__.keys():
            os.remove(self.__dict__[key][1]['PATH'])


db = Database()
