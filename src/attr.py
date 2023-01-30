# -*- coding: UTF-8 -*-
import arcpy
import arcpy.sa
import arcpy.da
import math


def __has_field(dataset,field):
	target_fields = filter(lambda x:x.name==field,arcpy.Describe(dataset).fields)
	return len(target_fields)>=1

def __field_type(dataset,field):
	target_fields = filter(lambda x:x.name==field,arcpy.Describe(dataset).fields)
	return target_fields[0].type

def __geo_type(dataset):
	return arcpy.Describe(dataset).shapeType

#utf8_field这个参数名称有点问题
def FieldStringReplace(dataset,field_name,old_pattern,new_pattern,utf8_field=True):
	cursor=arcpy.UpdateCursor(dataset)
	old_pattern=old_pattern.decode("utf8")
	new_pattern=new_pattern.decode("utf8")
	for row in cursor:
		str=row.getValue(field_name.decode("utf8"))
		if not utf8_field:
			str=str.encode("utf8")
		str2=str.replace(old_pattern,new_pattern)
		if not utf8_field:
			str2=str2.decode("utf8")
		if str!=str2:
			print(str+'  ->  '+str2)
		row.setValue(field_name.decode("utf8"),str2)
		cursor.updateRow(row)
	del row,cursor
	
	
# TEXT —名称或其他文本特性。 
# FLOAT —特定范围内含小数值的数值。 
# DOUBLE —特定范围内含小数值的数值。 
# SHORT —特定范围内不含小数值的数值；编码值。 
# LONG —特定范围内不含小数值的数值。 
# DATE —日期和/或时间。 
# BLOB —影像或其他多媒体。 
# RASTER —栅格影像。 
# GUID —GUID 值 

	
def FieldUpdater(dataset,field_name,rule=lambda x:x):
	cursor=arcpy.UpdateCursor(dataset)
	for row in cursor:
		value=row.getValue(field_name.decode("utf8"))
		new_value=rule(value)
		row.setValue(field_name.decode("utf8"),new_value)
		cursor.updateRow(row)
	del row,cursor
	
def FieldTypeChanger(dataset,field_name,field_type,field_precision=0,field_scale=0):
	arcpy.AddField_management(dataset, field_name+"_", field_type, field_precision, field_scale, field_scale)
	func_name={"TEXT":"str","FLOAT":"float","DOUBLE":"float","SHORT":"int","LONG":"long","DATE":"","BLOB":"","RASTER":"","GUID":""}
	arcpy.CalculateField_management(dataset, field_name+"_", func_name[field_type.upper()]+"( !"+field_name+"! )", "PYTHON_9.3", "#")
	arcpy.DeleteField_management(dataset,field_name)
	arcpy.AddField_management(dataset, field_name, field_type, field_precision, field_scale, field_scale)
	arcpy.CalculateField_management(dataset, field_name, "!"+field_name+"_!", "PYTHON_9.3", "#")
	arcpy.DeleteField_management(dataset,field_name+"_")
	
	
	
def FieldDefiner(dataset,field_name,value):
	cursor=arcpy.UpdateCursor(dataset)
	for row in cursor:
		row.setValue(field_name.decode("utf8"),value)
		cursor.updateRow(row)
	del row,cursor
	
	
#判断iden_dataset(点数据)分别能够被纳入多少个region_dataset中的面域内。符合条件的FID结果记录在record_field中，以逗号隔开。
#ContainsRecorder('待识别要素','文本字段','面要素','面ID')
def ContainsRecorder(iden_dataset,record_field,region_dataset,idenitiy_field):
	regions=[]
	for row in arcpy.da.SearchCursor(region_dataset,[idenitiy_field,"SHAPE@"]):
		regions.append(row)
	del row
	try:
		cursor=arcpy.da.UpdateCursor(iden_dataset,["SHAPE@",record_field.decode("utf8")])
	except:
		cursor=arcpy.da.UpdateCursor(iden_dataset,["SHAPE@",record_field])
	for row in cursor:
		comma=','
		for region in regions:
			if region[1].contains(row[0]):
				comma+=str(region[0])+','
		row[1]=comma
		cursor.updateRow(row)
	del row,cursor

def __mean(func,list):
	total = len(list)
	acc = 0.0
	for i in list:
		acc += func(i)
	return acc / total

#
#ContainsCounter('点要素','面要素','面统计字段')
def ContainsCounter(point_dataset,polygon_dataset,counter_field):
	if not __geo_type(point_dataset) == "Point":raise Exception("第1参数不是点要素")
	if not __geo_type(polygon_dataset) == "Polygon":raise Exception("第2参数不是面要素")
	if not __has_field(polygon_dataset,counter_field):raise Exception("第2参数没有目标字段")
	if not __field_type(polygon_dataset,counter_field) == "Integer":raise Exception("目标字段不是整型")
	
	polygons = []
	for row in arcpy.da.SearchCursor(polygon_dataset,["SHAPE@"]):
		polygons.append(row[0])
	del row
	
	min_x = arcpy.Describe(polygon_dataset).extent.XMin
	max_x = arcpy.Describe(polygon_dataset).extent.XMax
	min_y = arcpy.Describe(polygon_dataset).extent.YMin
	max_y = arcpy.Describe(polygon_dataset).extent.YMax
	tot_w = arcpy.Describe(polygon_dataset).extent.width
	tot_h = arcpy.Describe(polygon_dataset).extent.height
	mea_w = __mean(lambda x:x.extent.width,  polygons)
	mea_h = __mean(lambda x:x.extent.height, polygons)
	
	x_index = [set() for i in range(int(math.ceil(float(tot_w) / mea_w))+1)]
	y_index = [set() for i in range(int(math.ceil(float(tot_h) / mea_h))+1)]
	count = len(polygons)
	for row in range(count):
		ext = polygons[row].extent
		x_idx_min = int(math.ceil(float(ext.XMin - min_x) / mea_w))
		x_idx_max = int(math.ceil(float(ext.XMax - min_x) / mea_w))
		y_idx_min = int(math.ceil(float(ext.YMin - min_y) / mea_h))
		y_idx_max = int(math.ceil(float(ext.YMax - min_y) / mea_h))
		for xx in range(x_idx_min, x_idx_max + 1):
			x_index[xx].add(row)
		for yy in range(y_idx_min, y_idx_max + 1):
			y_index[yy].add(row)
	
	point_counts = [0 for i in range(len(polygons))]
	for row in arcpy.da.SearchCursor(point_dataset,["SHAPE@"]):
		if row[0]==None:
			continue
		point_xy = row[0].centroid
		x_idx = int(math.ceil(float(point_xy.X - min_x) / mea_w))
		y_idx = int(math.ceil(float(point_xy.Y - min_y) / mea_h))
		polygons_rough = x_index[x_idx].intersection(y_index[y_idx])
		for polygon_idx in list(polygons_rough):
			if polygons[polygon_idx].contains(row[0]):
				point_counts[polygon_idx]+=1
	del row
	
	cursor=arcpy.da.UpdateCursor(polygon_dataset,[counter_field])
	polygon_idx=0
	for row in cursor:
		row[0]=point_counts[polygon_idx]
		cursor.updateRow(row)
		polygon_idx+=1
	del row,cursor



#utf8_field这个参数名称有点问题
def FieldExtractor(dataset,field_name,utf8_field=True,key=lambda x:x):
	ll=set()
	cursor=arcpy.UpdateCursor(dataset)
	for row in cursor:
		str=row.getValue(field_name.decode("utf8"))
		if not utf8_field:
			str=str.encode("utf8")
		ll.add(str)
	del row,cursor
	return list(ll)


#utf8_field这个参数名称有点问题
def FieldLister(dataset,field_name,utf8_field=True,key=lambda x:x):
	ll=[]
	cursor=arcpy.da.SearchCursor(dataset,[field_name.decode("utf8")])
	for row in cursor:
		str=row[0]
		if not utf8_field:
			str=str.encode("utf8")
		ll.append(key(str))
	del row,cursor
	return ll


def edge_angle(edge_dataset,field_name):
	with arcpy.da.UpdateCursor(edge_dataset, ["SHAPE@",field_name]) as cursor:
		for row in cursor:
			edge=row[0].getPart()[0]
			if edge[1].X==edge[0].X:
				row[1]=0
			else:
				row[1]=math.atan((edge[1].Y-edge[0].Y)/(edge[1].X-edge[0].X))
			cursor.updateRow(row)
	
	
def XYGenerator(dataset,field_x,field_y):
	cursor=arcpy.UpdateCursor(dataset)
	for row in cursor:
		xy=row.getValue("Shape").centroid
		row.setValue(field_x.decode("utf8"),xy.X)
		row.setValue(field_y.decode("utf8"),xy.Y)
		cursor.updateRow(row)
	del row,cursor

#在照片转出的点要素基础上在targetpath目录中生成一个bat文件
#运行bat文件可以将选中的图片点要素照片硬连接到此处
def HardLinkGenerator(dataset,targetpath):
	fields = arcpy.Describe(dataset).fields
	field_names = list(map(lambda x:x.name,fields))
	path_field_id = field_names.index("Path")
	name_field_id = field_names.index("Name")
	# 没有以上两个字段会报错
	batch_here = targetpath+"/"+"_start_hard_link_.bat"
	fout = open(batch_here,"w")
	fout.write("setlocal")
	cursor = arcpy.da.SearchCursor(dataset,["Path","Name"])
	for row in cursor:
		path_value = row[0]
		name_value = row[1]
		command = "mklink /H \""+name_value.encode("cp936")+"\" \""+path_value.encode("cp936")+"\"\n"
		fout.write(command)
	del row,cursor
	fout.write("echo "+u"硬连接已完成。".encode("cp936")+"\n")
	fout.write("pause")
	fout.close()











