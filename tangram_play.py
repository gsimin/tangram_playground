import rhinoscriptsyntax as rs
import scriptcontext as sc
from Rhino.Geometry import Intersect, Point3d, Vector3d, Brep, BrepFace, BrepEdge, BrepVertex, Collections, NurbsCurve 
import scriptcontext
from operator import itemgetter
import math, random
import Rhino

tangram_dict = {}
modules_dict = {}
shape_list = []
keys = {}
face_list = []
func_list = []
trial = 2

class Operations:
    def __init__(self):
        self.connection_faces = []
        self.tangram1 = None
        self.tangram2= None
        self.starting_tangram = None
        self.target_tangram = None
        self.starting_face = None
        self.target_face = None
        self.vector = None
        self.key = None
        
    def select_highest_tangrams(self, key):
        face_map = {"square": 0, "rhombus": 1}
        tangrams = [value for value in tangram_dict[key].Values if value.get_type() != "triangle" and value.is_empty() and not value.is_selected()]
        
        if len(tangrams) == 0:
            return None
        selected_tangrams = []
        for tangram in tangrams:
            name = tangram.get_name()
            face_center = tangram.get_face_center(face_map[tangram.get_type()])
            center = tangram.get_center()
            if len(selected_tangrams) == 0:
                selected_tangrams.append((name, face_center, center))
            elif center[2] == selected_tangrams[0][1][2]:
                selected_tangrams.append((name, face_center, center))
            elif center[2] > selected_tangrams[0][1][2]:
                selected_tangrams = [(name, face_center, center)]
     
        return selected_tangrams
    
    def get_closest_face(self, tangram1, tangram2, key1, key2):
        result = None
        t1 = tangram_dict[key1][tangram1[0]]
        t2 = tangram_dict[key2][tangram2[0]]
        empty_faces1 = t1.get_empty_faces()
        empty_faces2 = t2.get_empty_faces()
        for face in empty_faces1:
            for face2 in empty_faces2:
                center1 = t1.get_face_center(face)
                center2 = t2.get_face_center(face2)
                distance = get_distance(center1, center2)
                if result == None:
                    result = (face, face2, distance)
                elif result[2] > distance:
                    result = (face, face2, distance)
        return result
        
    def pick_connection_tangrams(self, tangram_list1, tangram_list2, key1, key2):
        selected_tangrams = None
        for tangram1 in tangram_list1:
            for tangram2 in tangram_list2:
                result = self.get_closest_face(tangram1, tangram2, key1, key2)
                if selected_tangrams == None:
                    selected_tangrams = (tangram1[0], tangram2[0], result[0], result[1], result[2])
                elif result[2] < selected_tangrams[4]:
                    selected_tangrams = (tangram1[0], tangram2[0], result[0], result[1], result[2])
           
        return [(selected_tangrams[0], selected_tangrams[2]), (selected_tangrams[1], selected_tangrams[3])]
        
    def set_connection_tangrams(self, key1, key2):
        module1 = self.select_highest_tangrams(key1)
        module2 = self.select_highest_tangrams(key2)
        self.connection_faces = self.pick_connection_tangrams(module1, module2, key1, key2)
        self.tangram1 = tangram_dict[key1][self.connection_faces[0][0]]
        self.tangram2 = tangram_dict[key2][self.connection_faces[1][0]]
        self.select(self.connection_faces)
        
        
    def select(self, tangrams):
        self.tangram1.select(tangrams[0][1])
        self.tangram2.select(tangrams[1][1])
        
    def set_start_end(self):
        center1 = self.tangram1.get_connection_center(self.connection_faces[0][1])
        center2 = self.tangram2.get_connection_center(self.connection_faces[1][1])
        if center1[2] >= center2[2]:
            self.starting_tangram = self.tangram2
            self.target_tangram = self.tangram1
            self.starting_face = self.connection_faces[1][1]
            self.target_face = self.connection_faces[0][1]
        else:
            self.starting_tangram = self.tangram1
            self.target_tangram = self.tangram2
            self.starting_face = self.connection_faces[0][1]
            self.target_face = self.connection_faces[1][1]
        
    def connect(self, key1, key2):
        self.set_connection_tangrams(key1, key2)
        self.set_start_end()
        key = len(tangram_dict) + 1
        modules_dict[key] = type
        tangram_dict[key] = {}
        keys[key] = []
        self.key = key
        self.starting_tangram.create_first_connection_tangram("square_1", self.starting_face, True, self.starting_tangram.classification, 3, key)
        self.target_tangram.create_first_connection_tangram("square_2", self.target_face, False, self.target_tangram.classification, 3, key)
        self.vector = self.get_tangram("square_1").get_connection_vector(self.get_tangram("square_1"), self.get_target_tangram())
        valid = self.create_connections()
        return valid
        
    def create_connections(self):
        num_generation = 19
        index = 0
        key = self.key
        for i in range(num_generation):
            if index >= len(keys[key]):
                break
            tangram_dict[key][keys[key][index]].create_connection_tangram(self.get_target_tangram())
            index += 1
        valid = True
        for t in tangram_dict[key].Values:
            if valid == False:
                return valid
            valid = not self.check_intersection(t)
        return valid
            
                
    def check_intersection(self, t):
        other_keys = [i for i in keys.Keys if i != self.key]
        intersect = False
        for key in other_keys:
            if intersect == True:
                return intersect
            intersect = check_intersection(t.get_center(), rs.coercebrep(t.get_shape()), key)
        return intersect
            
        
    def get_target_tangram(self):
        return tangram_dict[self.key]["square_2"]
        
    def get_tangram(self, name):
        return tangram_dict[self.key][name]

class Tangram:
    shape_types = {"t": "triangle", "s": "square", "r": "rhombus"}
        
    def __init__(self, name, type, classification, shape, center, can_grow, key, occupied=None, target=None):
        self.name = name                                    # (str) name of the object
        self.type = type                                    # (str) type of the object
        self.classification = classification                # (int) 1 or 0
        self.shape = rs.coercebrep(rs.CopyObject(shape))    # (brep) shape of the object
        self.center = center                                # (list<float>) x,y,z coordinates of the center of the object
        self.can_grow = can_grow                            # (bool) true if object can grow
        self.face_dict = self.set_faces()                   # (dictionary) shows status of the faces of the object
        self.set_occupied_face(occupied)
        self.func = None                                    # (string) func of the object in the playground
        self.target_face = 0                                # (int)
        self.key = key
        self.selected = False
        self.create_growing = False
        
    def get_func(self):
        return self.func
        
    def get_name(self):
        """
        Output: (str) name of the oject
        """
        return self.name
        
    def get_shape(self):
        """
        Output: (Brep) shape of the object
        """
        return self.shape
        
    def get_center(self):
        """
        Output: (list<float>) x,y,z coordinates of the center
        """
        return self.center
        
    def get_type(self):
        """
        Output: (str) type of the object
        """
        return self.type
        
    def check_if_can_grow(self):
        return self.can_grow
        
    def get_faces(self):
        """
        Output: (List<BrepFace>) faces of the object
        """
        faces = Brep.Faces.GetValue(self.shape)
        return faces
        
    def set_create_growing(self, growing):
        self.create_growing = growing
        
    def get_face(self, index):
        faces = self.get_faces()
        face = faces[index]
        return face
        
    def get_edges(self):
        """
        Output: (List<BrepEdges>) edges of the object
        """
        edges = Brep.Edges.GetValue(self.shape) 
        return edges
        
    def get_vertices(self):
        """
        Output: (List<BrepVertices>) vertices of the object
        """
        vertices = Brep.Vertices.GetValue(self.shape)
        return vertices
        
    def get_empty_faces(self):
        return [face for face in self.face_dict.Keys if self.face_dict[face] == "empty"]
        
    def get_not_occupied_faces(self):
        return [face for face in self.face_dict.Keys if self.face_dict[face] == "empty" or self.face_dict[face] == "not_growing"]
        
    def get_occupied_faces(self):
        return [face for face in self.face_dict.Keys if self.face_dict[face] != "empty" and self.face_dict[face] != "not_growing" and self.face_dict[face] != "open"]
    
    def get_four_points(self, face_index):
        """
        Input: 
            face: (int) index of the face
        Output: (List<BrepVertex>) points of the face
        """
        edges = self.get_edges()
        face = self.get_face(face_index)
        frame_indexes = BrepFace.AdjacentEdges(face)
        frame = [edges[i] for i in frame_indexes]
        vertices = [BrepEdge.StartVertex.GetValue(i) for i in frame]
        end_vertices = [BrepEdge.EndVertex.GetValue(i) for i in frame]
        vertices.extend(end_vertices)
        locations = [BrepVertex.Location.GetValue(i) for i in vertices]
        sorted_locations = sort_points(locations)
        return sorted_locations
        
    def get_face_center(self, face_index):
        vertices = self.get_four_points(face_index)
        length = len(vertices)
        x_axis = round(sum([vertices[i][0] for i in range(length)]) / length, 2)
        y_axis = round(sum([vertices[i][1] for i in range(length)]) / length, 2)
        z_axis = round(sum([vertices[i][2] for i in range(length)]) / length, 2)
        center = [x_axis, y_axis, z_axis]
        return center
        
    def get_rotation(self, face_index):
        rotation_map = {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}
        vertices = self.get_four_points(face_index)
        length = len(vertices)
        x_axis = set([vertices[i][0] for i in range(length)])
        y_axis = set([vertices[i][1] for i in range(length)])
        if (len(x_axis) == 1):
            return rotation_map["x"]
            
        elif (len(y_axis) == 1):
            return rotation_map["y"]
            
        else:
            return rotation_map["z"]
                    
    def get_target_points(self, face_index):
        """
        Input: 
            face: (int) index of the face
        Output: (List<Point3d>) target points
        """
        vertices = self.get_four_points(face_index)
        target_points = [vertices[1], vertices[0], vertices[3]]
        return target_points
        
    def get_reference_shape(self, ref_object, target_srf_num):
        ref_points = ref_object.get_reference_points(target_srf_num)
        target_points = self.get_target_points(target_srf_num)
        new_shape = rs.OrientObject(rs.CopyObject(ref_object.shape), ref_points, target_points)
        if is_intersect(self.shape, rs.coercebrep(rs.CopyObject(new_shape))):
            new_shape = rs.OrientObject(rs.CopyObject(ref_object.shape), ref_object.get_target_points(self.target_face), target_points)
        return new_shape        
        
    def get_reference_points(self, target_index):
        """
        Input: 
            face: (int) index of the face
        Output: (List<Point3d>) reference points
        """
        vertices = self.get_four_points(self.target_face)
        return [vertices[0], vertices[1], vertices[2]]
        
    def get_growing_faces(self):
        selected_faces = []
        faces = [i for i in self.face_dict.Keys if self.face_dict[i] == "empty"]
        max = len(faces)
        if max == 0:
            return None
        if max == 1:
            selected_faces.append(faces[0])
            return selected_faces
        min = 1
        if max > 2:
            min = 2
        random.shuffle(faces)
        num = random.randrange(min, max) + 1
        for i in range(1, num):
            selected_faces.append(faces[i])
        return selected_faces
        
    def get_growing_tangram(self, shape_type):
        return tangram_map[shape_type]
        
    def generate(self):
        if self.can_grow:
            face_indexes = self.get_growing_faces()
            if face_indexes != None:
                for index in face_indexes:
                    tangram_type = self.get_growing_type(index)
                    self.create_shape(index, tangram_type)
    
    def create_shape(self, index, tangram_type, rotation=None):
        tangram_shape = None
        ref_tangram = self.get_growing_tangram(tangram_type)
        if tangram_type == self.shape_types["s"]:
            tangram_shape = create_shape(self, ref_tangram, index, 0)
        else:
            tangram_shape = create_shape(self, ref_tangram, index, rotation)
        center = find_center(Brep.Vertices.GetValue(rs.coercebrep(tangram_shape)))
        valid = check_if_valid(center, rs.coercebrep(tangram_shape), self.key)
        if valid:
            self.create_tangram(tangram_type, self.classification, tangram_shape, center, self.create_growing, (self.target_face, self.name), index) 
    
    def create_tangram(self, type, classification, shape, center, can_grow, occupied, index):
        name = type + "_" + str(len(shape_list)+1)
        tangram = None
        if type == self.shape_types["s"]:
            tangram = T_Square(name, type, classification, shape, center, can_grow, self.key, occupied)
        elif type == self.shape_types["t"]:
            tangram = T_Triangle(name, type, classification, shape, center, can_grow, self.key, occupied)
        else:
            tangram = T_Rhombus(name, type, classification, shape, center, can_grow, self.key, occupied)
        shape_list.append(shape)
        keys[self.key].append(name)
        self.set_occupied_face((index, name))
        tangram_dict[self.key][name] = tangram
        self.target_face = 0

    def set_faces(self):
        """
        Output: (dictionary) status of the faces of the object
        """
        face_dict = {}
        face_num = Collections.BrepFaceList.Count.GetValue(self.get_faces())
        for i in range(face_num):
            face_dict[i] = "empty"
        return face_dict
        
    def select(self, face_index):
        self.selected = True
        face_center = self.get_face_center(face_index)
        shape_list.append(rs.AddPoint(self.center))
        shape_list.append(rs.AddPoint(face_center))
        
    def unselect(self):
        self.selected = False
        
    def is_selected(self):
        return self.selected
        
    def set_occupied_face(self, occupied):
        """
        Input:
            occupied: (tuple<int, str>) index of the face that is occupied, name of the object added to the face
        """
        if occupied != None:
            self.face_dict[occupied[0]] = occupied[1]
            
    def is_empty(self):
        count = 0
        for value in self.face_dict.Values:
            if value == "empty":
                count += 1
        return count > 0
        
    def create_first_connection_tangram(self, name, face_index, can_grow, type, classification, key):
        tangram_shape = create_square_shape(self, tangram_map["square"], face_index)
        center = find_center(Brep.Vertices.GetValue(rs.coercebrep(tangram_shape)))
        if (type == 1):
            rs.MoveObject(tangram_shape, [0,0,-1])
            center = [center[0], center[1], center[2]-1]
        tangram = T_Square(name, "square", classification, tangram_shape, center, can_grow, key, (self.target_face, self.name))
        shape_list.append(tangram_shape)
        keys[key].append(name)
        self.set_occupied_face((face_index, name))
        #self.set_func("bridge")
        tangram_dict[key][name] = tangram
        
    def get_connection_angle(self, shape_type, ref_tangram, face_index, vector):
        if shape_type == "square":
            return 0
        elif math.fabs(vector[2]) > 0:
            return 0 
        else:
            shape1 = create_shape(self, ref_tangram, face_index, 90)
            center1 = find_center(Brep.Vertices.GetValue(rs.coercebrep(shape1)))
            distance1 = get_distance(vector, center1)
            shape2 = create_shape(self, ref_tangram, face_index, 270)
            center2 = find_center(Brep.Vertices.GetValue(rs.coercebrep(shape2)))
            distance2 = get_distance(vector, center2)
            if distance1 <= distance2:
                return 90
            return 270
        
    def create_connection_tangram(self, target_tangram):
        if self.can_grow:
            vector = self.get_connection_vector(self, target_tangram)
            ref_type = self.get_connection_type(vector)
            ref_tangram = self.get_growing_tangram(ref_type) 
            face_index = self.get_connection_face(vector)
            can_grow = get_distance(self.center, target_tangram.get_center()) > 2
            angle = self.get_connection_angle(ref_type, ref_tangram, face_index, vector)
            tangram_shape = create_shape(self, ref_tangram, face_index, angle)
            center = find_center(Brep.Vertices.GetValue(rs.coercebrep(tangram_shape)))
            shape_list.append(rs.AddPoint(center))
            self.create_tangram(ref_type, self.classification, tangram_shape, center, can_grow, (self.target_face, self.name), face_index)
        
    def get_connection_vector(self, tangram, target_tangram):
        center1 = tangram.get_center()
        center2 = target_tangram.get_center()
        x = center2[0] - center1[0]
        y = center2[1] - center1[1]
        z = center2[2] - center1[2]
        return ([x, y, z])        
        
    def get_occupied_type(self, face_index):
        name = self.face_dict[face_index]
        index = name.rindex("_")
        return name[:index]
        
    def set_func(self, func):
        self.func = func
                    

    def get_final_shape(self):
        if self.get_center()[2] <= 0:
            return [self.get_face(i) for i in self.face_dict.Keys]
        not_occupied_faces = self.get_not_occupied_faces()
        return [self.get_face(i) for i in not_occupied_faces]
        
    def set_layer(self):
        if self.func == None:
            return "None"
        return self.func    
        
    def finalize(self):
        self.set_func(self.determine_func())
        func_list.append(self.func)
        self.arrange_shape()
        faces = self.get_final_shape()
        for face in faces:
            face_list.append(face)

    def bake(self):
        doc_object = rs.coercerhinoobject(rs.CopyObject(self.shape), True, True)
        geometry = doc_object.Geometry
        attributes = doc_object.Attributes
        scriptcontext.doc = Rhino.RhinoDoc.ActiveDoc
        layer = self.set_layer()
        if not rs.IsLayer(layer): 
            rs.AddLayer(layer)
        rhino_brep = scriptcontext.doc.Objects.Add(geometry, attributes)
        rs.ObjectLayer(rhino_brep, layer)
        scriptcontext.doc = ghdoc
        
class T_Square(Tangram):
    def __init__(self, name, type, classification, shape, center, can_grow, key, occupied=None):
        Tangram.__init__(self, name, type, classification, shape, center, can_grow, key, occupied)
        self.create_growing = True          # can create growing objects
        self.set_growing_faces()
    
    def get_growing_type(self, face_index):
        """
        Input:
            face_index: (int) index of the face to grow
        Output: (str) type of the shape 
        """
        if face_index == 4:
            self.create_growing = False
            return self.shape_types["t"]
        self.create_growing = True
        return random.choice(self.shape_types.Values)
        
    def set_growing_faces(self):
        growing_faces = [0, 1, 2, 3]
        if self.classification == 1:
            growing_faces.append(4)
        for index in self.face_dict.Keys:
            if index not in growing_faces:
                self.face_dict[index] = "not_growing"
                
    def get_growing_faces(self):
        selected_faces = Tangram.get_growing_faces(self)
        if self.classification == 1 and self.face_dict[4] == "empty" and 4 not in selected_faces:
            selected_faces.append(4)
        return selected_faces
                
    def get_connection_center(self, face):
        return self.get_face_center(face)
        
    def get_connection_type(self, vector):
        if vector[2] == 0:
            if math.fabs(vector[0]) + math.fabs(vector[1]) >= 4 and math.fabs(vector[0]) >= 2 and math.fabs(vector[1]) >= 2:
                return "rhombus"
            return "square"
        return "rhombus"
        
    def get_connection_face(self, vector):
        center0 = self.get_face_center(0)
        center1 = self.get_face_center(1)
        center2 = self.get_face_center(2)
        center3 = self.get_face_center(3)
        x_growth = []
        y_growth = []
        if center1[0] == center3[0]:
            y_growth.append((1, center1[1]))
            y_growth.append((3, center3[1]))
            x_growth.append((2, center2[0]))
            x_growth.append((0, center0[0]))
        else:
            x_growth.append((1, center1[0]))
            x_growth.append((3, center3[0]))
            y_growth.append((2, center2[1]))
            y_growth.append((0, center0[1]))
        sorted_x = sorted(x_growth, key=itemgetter(1))
        sorted_y = sorted(y_growth, key=itemgetter(1))
        if math.fabs(vector[0]) > math.fabs(vector[1]):
            selected = self.get_connection_x_axis(vector, sorted_x)
            if selected != 0:
                return selected
            return self.get_connection_y_axis(vector, sorted_y)
        else:
            selected = self.get_connection_y_axis(vector, sorted_y)
            if selected != 0:
                return selected
            return self.get_connection_x_axis(vector, sorted_x)
                
    def get_connection_x_axis(self, vector, x_axis):
        if vector[0] < 0:
            return x_axis[0][0]
        else:
            return x_axis[-1][0]
            
    def get_connection_y_axis(self, vector, y_axis):
        if vector[1] < 0:
            return y_axis[0][0]
        else:
            return y_axis[-1][0]
            
    def check_occupied_faces(self, faces):
        if 1 in faces and 3 in faces:
            return [1, 3]
        elif 0 in faces and 2 in faces:
            return [0, 2]
        return None
                
    def determine_func(self):
        if self.func == None:
            if self.classification == 1:
                return "semi_open"
            occupied_faces = self.get_occupied_faces()
            selected_occupied_faces = self.check_occupied_faces(occupied_faces)
            if selected_occupied_faces == None:
                if self.classification == 3:
                    return "bridge"
                return "platform"
            else:
                types = [self.get_occupied_type(i) for i in  selected_occupied_faces]
                if types[0] == types[1] and types[0] == self.shape_types["s"]:
                    other_occupied = [i for i in occupied_faces if i not in selected_occupied_faces]
                    if len(other_occupied) == 0:
                        return "net"
                    else:
                        can_stand = True
                        for o in other_occupied:
                            if can_stand == False:
                                break
                            name = self.face_dict[o]
                            tangram = tangram_dict[self.key][name]
                            can_stand = tangram.can_stand()
                        if can_stand:
                            return "net"
                        elif self.classification == 3:
                            return "bridge"
                        return "platform"
                else:
                    if self.classification == 3:
                        return "bridge"
                    return "platform"
        return self.func
               
    def can_stand(self):
        return True
        
    def arrange_shape(self):
        if self.get_center()[2] <= 0 :
            return
        if self.func == "platform" or self.func == "semi_open":
            empty_faces = self.get_empty_faces()
            openings = [f for f in empty_faces if f != 4]
            if len(empty_faces) > 0:
                self.face_dict[random.choice(empty_faces)] = "open"

class T_Triangle(Tangram):
    def __init__(self, name, type, classification, shape, center, can_grow, key, occupied=None):
        Tangram.__init__(self, name, type, classification, shape, center, can_grow, key, occupied)
        self.set_growing_faces()
        
    def is_open(self):
        return shelf.face_dict[2] == "open"
    
    def get_growing_type(self, face_index):
        """
        Input:
            face_index: (int) index of the face to grow
        Output: (str) type of the shape 
        """
        if face_index == 2:
            self.target_face = 2
            return self.shape_types["r"]
        return random.choice([self.shape_types["t"], self.shape_types["r"]])
        
    def set_growing_faces(self):
        growing_faces = [0]
        if self.get_rotation(1)[2] != 1:
            growing_faces.append(1)
        for index in self.face_dict.Keys:
            if index not in growing_faces:
                self.face_dict[index] = "not_growing"
                
    def can_stand(self):
        vertices = self.get_four_points(2)
        length = len(vertices)
        x_axis = set([vertices[i][0] for i in range(length)])
        y_axis = set([vertices[i][1] for i in range(length)]) 
        z_axis = set([vertices[i][1] for i in range(length)])
        if len(x_axis) + len(y_axis) + len(z_axis) > 4:
            return False
        return True
        
    def arrange_shape(self):
        if self.func == "platform" or self.func == "semi_open":
            if self.get_center()[2] > 0.5:
                self.face_dict[random.choice([3, 4])] = "open"
            else:
                self.face_dict[2] = "open"
        
    def determine_func(self):
        if self.func != None:
            return self.func
        if self.classification == 1:
            return "semi_open"
        else:
            if find_index(self.key, self.name) == 1:
                return "access_on"
            name = self.face_dict[0]
            tangram = tangram_dict[self.key][name]
            occupied_func = tangram.get_func()
            if occupied_func == "net":
                return "platform_closed"
            else:
                return "platform"
        
class T_Rhombus(Tangram):
    def __init__(self, name, type, classification, shape, center, can_grow, key, occupied=None):
        Tangram.__init__(self, name, type, classification, shape, center, can_grow, key, occupied)
        self.set_growing_faces()
    
    def get_growing_type(self, face_index):
        """
        Input:
            face_index: (int) index of the face to grow
        Output: (str) type of the shape 
        """
        if self.classification == 1:
            return self.shape_types["s"]
        return random.choice([self.shape_types["r"], self.shape_types["s"]])
        
    def set_growing_faces(self):
        growing_faces = [0, 1]
        for index in self.face_dict.Keys:
            if index not in growing_faces:
                self.face_dict[index] = "not_growing"
                
    def get_connection_center(self, face):
        return self.get_face_center(face)
        
    def get_connection_vector(self, tangram, target_tangram):
        center1 = tangram.get_center()
        center2 = target_tangram.get_center()
        x = center2[0] - center1[0]
        y = center2[1] - center1[1]
        z = center2[2] - center1[2]
        return ([x, y, z - 0.5])
        
    def get_connection_face(self, vector):
        return 1
        
    def get_connection_type(self, vector):
        return "square"
        
    def is_decrease(self):
        center1 = self.get_face_center(0)
        center2 = self.get_face_center(1)
        return center1[2] > center2[2]
        
    def can_stand(self):
        center1 = self.get_face_center(0)
        center2 = self.get_face_center(1)
        return center1[2] == center2[2]
        
    def arrange_shape(self):
        if self.func == "platform" or self.func == "semi_open":
            if self.face_dict[1] == "empty":
                self.face_dict[1] = "open"
        
    def determine_func(self):
        if self.func != None:
            return self.func
        if not self.can_stand():
            if len(self.get_empty_faces()) == 0 and self.get_occupied_type(1) == "rhombus":
                if self.is_decrease():
                    return "arc"
                name = self.face_dict[1]
                tangram = tangram_dict[self.key][name]
                if tangram.is_decrease():
                    return "arc"
                else:
                    if self.classification == 1:
                        return "access_in"
                    return "access_on"                    
            else:
                if self.classification == 1:
                    return "access_in"
                return "access_on"
        else:
            if self.classification == 3:
                return "bridge"
            name = self.face_dict[0]
            tangram = tangram_dict[self.key][name]
            occupied_func = tangram.get_func()
            if occupied_func == "net":
                return "platform_closed"
            else:
                if self.classification == 1:
                    return "semi_open"
                return "platform"
        
def sort_points(points):
    """
    Input:
        points: (List<Point3d>)
    Output: (List<Point3d>) points ordered by z, y, and x axes 
    """
    point_list = []
    for i in range(len(points)):
        point = (points[i][0], points[i][1], points[i][2])
        if point not in point_list:
            point_list.append(point)
    sorted_points = sorted(point_list, key=itemgetter(2,1,0), reverse=True)
    return sorted_points
    
def find_center(vertices):
    """
    Input:
        vertices: (List<BrepVertex>) vertices of the object
    Output: (List<float>) center location of the object
    """
    vertex_num = Collections.BrepVertexList.Count.GetValue(vertices)
    x_axis = round(sum([BrepVertex.Location.GetValue(i)[0] for i in vertices]) / vertex_num, 2)
    y_axis = round(sum([BrepVertex.Location.GetValue(i)[1] for i in vertices]) / vertex_num, 2)
    z_axis = round(sum([BrepVertex.Location.GetValue(i)[2] for i in vertices]) / vertex_num, 2)
    center = [x_axis, y_axis, z_axis]
    return center
    
def get_distance(center1, center2):
    """
    Input:
        center1: (List<float>) center of the object1
        center2: (List<float>) center of the object2
    Output: (float) distance between two centers 
    """
    distance = math.sqrt((center1[0] - center2[0]) ** 2 + (center1[1] - center2[1]) ** 2 + (center1[2] - center2[2]) ** 2)
    return distance
    
def check_if_valid(center, shape, key):
    valid_location = check_location(center)
    intersect = check_intersection(center, shape, key)
    return valid_location and not intersect
    
def check_location(center):
    if 0 < center[2] < 3:
        return True
    return False
    
def check_intersection(center, shape, key):
    intersect = False
    for tangram in tangram_dict[key].Values:
        if intersect == True:
            break;
        t_center = tangram.get_center()
        distance = get_distance(t_center, center)
        if get_distance(t_center, center) < 1.5:
            intersect = is_intersect(tangram.get_shape(), shape)
    return intersect
    
def is_intersect(object1, object2):
    v = Intersect.Intersection.BrepBrep(object1, object2, 0.05)
    if len(v[1]) > 0: 
        points = []
        for p in v[1]:
            points.append(NurbsCurve.PointAtEnd.GetValue(p))
            points.append(NurbsCurve.PointAtStart.GetValue(p))
        point_x = set([Point3d.X.GetValue(i) for i in points])
        point_y = set([Point3d.Y.GetValue(i) for i in points])
        point_z = set([Point3d.Z.GetValue(i) for i in points])
        if len(point_x) < 2 or len(point_y) < 2 or len(point_z) < 2:
            return False
        return True
    return False
    
def get_ref_pts(ref_obj, srf_num, indexes):
    obj_copy = rs.CopyObject(ref_obj)
    all_srf = rs.ExplodePolysurfaces(obj_copy)
    ref_srf = rs.DuplicateSurfaceBorder(all_srf[srf_num])
    ref_lines = rs.ExplodeCurves(ref_srf)
    ref_points = [rs.CurveEndPoint(ref_lines[indexes[0]]), rs.CurveEndPoint(ref_lines[indexes[1]]), rs.CurveEndPoint(ref_lines[indexes[2]])]
    return ref_points

def create_square_shape(target_object, ref_object, target_srf_num):
    shape = target_object.get_reference_shape(ref_object, target_srf_num)
    return shape
    
def create_shape(target_object, ref_object, target_srf_num, angle=None):
    if angle == None:
        angle = random.choice([0, 90, 180, 270])
    ref_points = ref_object.get_reference_points(target_srf_num)
    target_points = target_object.get_target_points(target_srf_num)
    shape = target_object.get_reference_shape(ref_object, target_srf_num)
    rotation_axis = target_object.get_rotation(target_srf_num)
    center = target_object.get_face_center(target_srf_num)
    rs.RotateObject(shape, center, angle, rotation_axis)
    return shape
    
def move(shape, vector):
    new_shape = rs.MoveObject(rs.CopyObject(shape), vector) 
    return new_shape
    


def create_module(generation, tangram, shape, type, key):
    starting_dict = {0: {"index": random.choice([0, 1, 2, 3]), "rotation": 0, "type": "triangle", "func": "access"},
                     1: {"index": 4, "rotation": random.choice([0, 90, 180, 270]), "type": "triangle", "func": "semi_open" }}
    num_generation = generation
    index = 0
    shape_list.append(shape)
    modules_dict[key] = type
    tangram_dict[key] = {}
    keys[key] = []
    tangram_dict[key]["square_1"] = tangram
    tangram_dict[key]["square_1"].set_create_growing(False)
    tangram_dict[key]["square_1"].create_shape(starting_dict[type]["index"], starting_dict[type]["type"], starting_dict[type]["rotation"])
    keys[key].append("square_1")
    i = 0
    while i < num_generation:
        if index >= len(keys[key]):
            break
        t = tangram_dict[key][keys[key][index]]
        t.generate()
        if not t.check_if_can_grow():
            i += 1
        index += 1
        
        

def finalize():
    major_keys = sorted(keys.Keys)
    for key in major_keys:
        square_list = [i for i in keys[key] if i.startswith("s")]
        sorted_s_list = sorted(square_list)
        for s in sorted_s_list: 
            tangram_dict[key][s].finalize()
            
        rhombus_list = [i for i in keys[key] if i.startswith("r")]
        sorted_r_list = sorted(rhombus_list)
        for r in sorted_r_list: 
            tangram_dict[key][r].finalize()
            
        triangle_list = [i for i in keys[key] if i.startswith("t")]
        sorted_t_list = sorted(triangle_list)
        for t in sorted_t_list: 
            tangram_dict[key][t].finalize()
            
        full_list = keys[key]
        sorted_full_list = sort_module(key)
        for t in sorted_full_list:
            tangram_dict[key][t].bake()            

def sort_module(key):
    key_list = [i for i in keys[key]]
    sorted_key_list = sorted(key_list, key=sort_tangrams)
    return (sorted_key_list)
    
def find_index(key, name):
    sorted_list = sort_module(key)
    return sorted_list.index(name)
    
def sort_tangrams(name):
    index = name.index("_") + 1
    return name[index:] 
    
def initialize(type, location):
    function_map = {0: "platform", 1:"semi_open"}
    name = "square_1"
    vector = location
    starting_shape = move(square, vector)
    center = find_center(Brep.Vertices.GetValue(rs.coercebrep(starting_shape)))
    key = len(tangram_dict.Keys) + 1
    starting_tangram = T_Square(name, "square", type, starting_shape, center, True, key)
    starting_tangram.set_func(function_map[type])
    
    return [starting_tangram, starting_shape]
    
def reset():
    global tangram_dict, shape_list, keys, face_list, modules_dict
    tangram_dict = {}
    modules_dict = {}
    shape_list = []
    keys = {}
    face_list = []
    func_list = []
    main()
    
    
def get_user_input():
    modules = []
    module_num = rs.GetInteger("Number of modules (2-5):", 2, 2, 5)

    for num in range(module_num):
        type = rs.GetInteger("Module type (0-1):", 0, 0, 1)
        gen_num = rs.GetInteger("Number of generation (1-5):", 1, 1, 5)
        x = rs.GetInteger("X coordinate (min 5):", 5, 5)
        y = rs.GetInteger("Y coordinate (min 5):", 5, 5)
        modules.append([type, gen_num, x, y])
    return modules
    
def set_user_input():
    return [{"type": type1, "gen": generation1, "vector": location1 }, 
            {"type": type2, "gen": generation2, "vector": location2}]
            

def main():
    global trial
    modules = set_user_input()
    for m in modules:
        key = len(tangram_dict) + 1
        initials = initialize(m["type"], m["vector"])
        create_module(m["gen"], initials[0], initials[1], m["type"], key)
        
    operations = Operations()
    connected_modules = sorted([i for i in modules_dict.Keys])
    
    valid = True
    for i in range(len(connected_modules) - 1):
        if valid == False:
            break
        valid = operations.connect(connected_modules[i], connected_modules[i+1])
    if valid:
        finalize()
    else:
        trial -= 1
        if trial >= 0:
            print("a")
            reset()
            


square_ref = T_Square("square-1", "square", 0, square, [0.5,0.5,0.5], True, None)
triangle_ref = T_Triangle("triangle-2", "triangle", 0,  triangle, [0,0,0], False, None)
rhombus_ref = T_Rhombus("rhombus-3", "rhombus", 0, rhombus, [0,0,0], False, None)
tangram_map = {"square": square_ref, "triangle": triangle_ref, "rhombus": rhombus_ref}
    
if start:   
    main()
    

playground_tool = len(face_list)
        