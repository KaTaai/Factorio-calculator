'''
Created on Jul 22, 2019

@author: kataai
'''
import json
import sys

from anytree import Node, RenderTree


def parseQuestion(questionFileName):
    '''
    Parses the question file.
    @param questionFileName: a file name to a Json file
    @type questionFileName: a string
    '''

    with open(questionFileName) as questionFile:
        question = json.load(questionFile)

#     print(json.dumps(question, indent=4))
    Produce = question.get("Produce", None)
    produceList = []
    if Produce:
        #         print(json.dumps(Produce, indent=4))
        for p in Produce:
            produceList.append(p)
    Limit = question.get('Limit', None)
    if Limit:
        limit = Limit
    else:
        limit = []
    Mainbus = question.get('Mainbus', None)
    if Mainbus:
        mainbus = Mainbus
    else:
        mainbus = []

    return produceList, mainbus, limit


def parseFactorioItems(factorioItemsFileName):
    '''
    Parses the Factorio_items file and creates the machines and recipes
    @param factorioItemsFileName: a file name to a Json file
    @type factorioItemsFileName: a string

    @return: 1 array, 1 dict: recipeList, a list of Recipe objects. And machineDict a Dict of Machine objects with the category as key

    '''

    with open(factorioItemsFileName) as factorioItemsFile:
        factorioData = json.load(factorioItemsFile)

    Recipes = factorioData.get("Recipes", None)
    recipeList = []
    if Recipes:
        #         print(json.dumps(Produce, indent=4))
        for recipeName, recipeContents in Recipes.items():
            recipeArgs = {}
            involvesFluids = recipeContents.get("Involves fluids", None)

            if involvesFluids:
                recipeArgs["Involves fluids"] = involvesFluids

            r = Recipe(recipeName, recipeContents["Outputs"], recipeContents["Origin"],
                       recipeContents["Speed"], recipeContents['Ingredients'], recipeArgs)

            recipeList.append(r)

    Machines = factorioData.get("Machines", None)
    machineDict = {}
    if Machines:
        for machineName, machineDetails in Machines.items():
            handlesFluids = machineDetails.get("Handles fluids", None)
            machineArgs = {}
            level = machineDetails.get("Level", None)
            if level:
                machineArgs["Level"] = level
            if handlesFluids:
                machineArgs["Handles fluids"] = handlesFluids

            maxNumIngredients = recipeContents.get("Max # ingredients", None)
            if maxNumIngredients:
                recipeArgs["Max # ingredients"] = maxNumIngredients

            m = Machine(
                machineName, machineDetails["Category"], machineDetails["Speed"], machineArgs)

            if m.productionCategory in machineDict.keys():
                machineDict[m.productionCategory].append(m)
            else:
                machineDict[m.productionCategory] = [m]

    return recipeList, machineDict


class Recipe:
    def __init__(self, recipeName, outputs, productionCategory, productionTime, ingredients, *args):
        self.recipeName = recipeName
        self.outputs = outputs
        self.productionCategory = productionCategory
        self.productionTime = productionTime
        self.ingredients = ingredients
        self.__involvesfluids = args[0].get("Involves fluids", False)

    def involvesfluids(self):
        return self.__involvesfluids

    def __str__(self):

        # converts {ingredients} into {outputs}'
        return f'The recipe {self.recipeName}'

    def __repr__(self):
        return self.__str__()


class Machine:
    def __init__(self, machineName, productionCategory, speedModifier, *args):
        self.machineName = machineName
        self.productionCategory = productionCategory
        self.speedModifier = speedModifier
        self.level = args[0].get("Level", 1)
        self.maxNumberOfIngredients = args[0].get(
            "Max # ingredients", sys.maxsize)
        self.fluidCapable = args[0].get("Handles fluids", False)

    def isRecipeCompatible(self, Recipe):
        # productionCategory matches
        if not self.productionCategory in Recipe.productionCategory:
            return False

        # Not too many ingredients for the machine
        if self.maxNumberOfIngredients < len(list(Recipe.ingredients.keys())):
            return False

        # Fluids required and fluidcapable check
        if Recipe.involvesfluids() and not self.isFluidCapable():
            return False

        return True

    def isFluidCapable(self):
        return self.fluidCapable

    def __str__(self):
        return f'The machine {self.machineName} is a machine of the category {self.productionCategory}'

    def __repr__(self):
        return self.machineName


def createTree(itemName, recipeList, mainbus):
    '''
    Creates the full tree until the mainbus or no new recipes are found to connect
    @param itemName: The item that you want to start producing (Gets produced by the root of the tree)
    @type itemName: a String

    @param recipeList: a list of Recipe objects
    @type recipeList: a list

    @param mainbus: a list of strings of items on the mainbus
    @type mainbus: a list

    @return: The root of the tree or None
    '''
    rootRecipe = None
#     print(f'To be produced: {itemName}')
#     if itemName in mainbus:
#         return None
    for r in recipeList:
        #         print(r.recipeName)
        if not rootRecipe and itemName in r.outputs:
            print(r.recipeName)
            rootRecipe = Node(name=r.recipeName, recipe=r,
                              mainbusIngredients=[])
#             recipeList.remove(r)
#             print(f'{r.recipeName} added as a root')
    # check to see if the tree needs to be expanded and call recursively
    if rootRecipe:
        mainbusIngredients = rootRecipe.mainbusIngredients
        children = []
        for i in rootRecipe.recipe.ingredients:
            branche = createTree(i, recipeList, mainbus)
            if branche:
                #                 print('This item has a further step')
                children.append(branche)
            else:
                #                 print('This ingredient is a mainbus item, or an end item')
                mainbusIngredients.append(i)

        rootRecipe = Node(name=rootRecipe.name, children=children,
                          recipe=rootRecipe.recipe, mainbusIngredients=mainbusIngredients)
        return rootRecipe
    else:
        return None


def consolidateDicts(firstDict, secondDict):
    '''
    Consolidates the two dicts
    '''
    endDict = firstDict
    for k, v in secondDict.items():
        if k in endDict.keys():
            # The first dict already contains this tree
            endDict[k]['Rate'] += v['Rate']
        else:
            # This tree is new to the first dict
            endDict[k] = v
            pass
    return endDict


def subdivideTree(tree, productionRate, mainbus):
    '''
    Subdivides a given tree into sections of produce till the mainbus items or raw items, mainbus items till mainbus items, or mainbus items till raw materials
    @param tree: The tree to be subdivided
    @type tree: a tree of the class Node

    @param productionRate: The rate at which the product is produced (products per second)
    @type productionRate: a floating point number

    @param mainbus: an array of items on the mainbus
    @type mainbus: an array

    @return: a Dict of dicts with the product name as key and the tree, and productionRate inside as additional keys
        '''
#     print(f'we are subdividing: {tree.name}')

    # traverse tree
    # Check if child product in mainbus if yes, subdivide
    # call this function on the child, separate it from this tree
    # elif child not on mainbus, call this function but do not split
    # on the way back up consolidate the dicts about the root of the trees
    completeTreeDict = {}
    if tree.children:
        #         childrenList = tree.children
        for child in tree.children:

            producesMB = False
            for output in child.recipe.outputs:
                if output in mainbus:
                    producesMB = True
                    break
            if producesMB:
                # This child produces a mainbus item
                #                 print('A mainbus item')
                # gets the ingredient that it's about
                targetedIngredient = [
                    value for value in tree.recipe.ingredients if value in child.recipe.outputs]
                targetedIngredient = targetedIngredient[0]
#                 print(targetedIngredient)
#                 print(tree.recipe.ingredients[targetedIngredient])
                productionRateChild = productionRate * \
                    child.recipe.outputs[targetedIngredient]

                # Removes the child from the tree and tries again
                child.parent = None
                tree.mainbusIngredients.append(targetedIngredient)
                temp = subdivideTree(child, productionRateChild, mainbus)
#                 print(f'temp: {temp}')
                tempParent = {targetedIngredient: {
                    "Rate": productionRateChild,
                    "Tree": child}}
                completeTreeDict = consolidateDicts(completeTreeDict, temp)
                completeTreeDict = consolidateDicts(
                    completeTreeDict, tempParent)
                pass
            else:
                # This child produces an item that is not a mainbus item
                #                 print('Not a mainbus item')
                # gets the ingredient that it's about
                targetedIngredient = [
                    value for value in tree.recipe.ingredients if value in child.recipe.outputs]
                targetedIngredient = targetedIngredient[0]
#                 print(targetedIngredient)
                productionRateChild = productionRate * \
                    tree.recipe.ingredients[targetedIngredient]
                temp = subdivideTree(child, productionRateChild, mainbus)
                completeTreeDict = consolidateDicts(completeTreeDict, temp)
                pass
    else:
        # This produces a raw material
        #         completeTreeDict = consolidateDicts(
        #             completeTreeDict, {"This is a raw material": {'Rate': 69, 'Tree': tree}})
        #         print(f'A raw material: {completeTreeDict}')
        pass

    return completeTreeDict


def calculateMachines(Tree, Rate, machineDict, limit):
    from math import ceil
    outputname = list(Tree.recipe.outputs.keys())[0]
    machineChoices = machineDict.get(Tree.recipe.productionCategory[0], None)
    chosenMachine = None
    for machine in machineChoices:
        if machine.machineName in limit:
            chosenMachine = machine
    if not chosenMachine:
        for machine in machineChoices:
            if not chosenMachine:
                if machine.isRecipeCompatible(Tree.recipe):
                    chosenMachine = machine
            else:
                if chosenMachine.level < machine.level and machine.isRecipeCompatible(Tree.recipe):
                    chosenMachine = machine

    # the amount of machines needed at 1.0 x speed
    numberMachines = (Rate * Tree.recipe.productionTime /
                      Tree.recipe.outputs[outputname]) / chosenMachine.speedModifier

    print('\n'.join([f'Product: {outputname}',
                     f'Produce: {Rate}',
                     f'# machines: {numberMachines} Number machines rounded: {ceil(numberMachines)} Which machine: {chosenMachine.machineName}',
                     'Ingredients:', '\n'.join([f'{Rate*v} {k}' for k, v in Tree.recipe.ingredients.items()]), '']))

    if Tree.children:
        for child in Tree.children:
            childRate = Tree.recipe.ingredients[list(
                child.recipe.outputs.keys())[0]] * Rate
            calculateMachines(child, childRate, machineDict, limit)
    pass


if __name__ == '__main__':
    print("We've started!\n")
    argv = sys.argv
    produceList, mainbus, limit = parseQuestion(argv[1])

    recipeList, machineDict = parseFactorioItems('Factorio_items.json')

#     print(machineDict)

    produceDict = {}
    for Item in produceList:
        firstNode = createTree(Item['Produce'], recipeList, mainbus)

        produceDict = consolidateDicts(
            produceDict, {Item['Produce']: {'Rate': Item['Amount'], 'Tree': firstNode}})
        produceDict = consolidateDicts(
            produceDict, subdivideTree(firstNode, Item['Amount'], mainbus))

#     print()  # produceDict)
    for k, v in produceDict.items():
        calculateMachines(v['Tree'], v['Rate'], machineDict, limit)
#         print(f'{v["Rate"]} {k} per second')
#         print(RenderTree(v['Tree']), '\n\n')

    pass
