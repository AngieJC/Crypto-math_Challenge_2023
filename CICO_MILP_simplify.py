import gurobipy as gp
from gurobipy import GRB

step = 4 - 1 # 步数
v_num = 4 # 变量个数
e_max = 99 # 每个方程设定次数不超过这个值，做整数变量上界用
d_max = 99 # 每个位置作为现有未知数的表达式的次数不超过这个值，做整数变量上界用
e_sum_max = 10000 # 所有方程次数之和不超过这个值，定义目标函数变量时做上界用

def is_lower(s, j): # 判断这个位置是不是下游位置
    result = True
    if s % 2 == 0:
        if j in [1, 4]:
            result = True
        else:
            result = False
    else:
        if j in [0, 2, 3, 5]:
            result = True
        else:
            result = False
    return result

def get_upper(s, j):
    upper = []
    if s % 2 == 0: # 若 s 为偶数
        if j == 1:
            upper.append(s - 1)
            upper.append(4)
        elif j == 4:
            upper.append(s + 1)
            upper.append(1)
    else:
        if j == 0:
            upper.append(s - 1)
            upper.append(3)
        elif j == 2:
            upper.append(s - 1)
            upper.append(5)
        elif j == 3:
            upper.append(s + 1)
            upper.append(0)
        elif j == 5:
            upper.append(s + 1)
            upper.append(2)
    return upper

def get_lower(s, j):
    lower = [None] * 2
    if s % 2 == 1: # 若s为奇数
        if j == 1:
            lower[0] = s - 1
            lower[1] = 4
        elif j == 4:
            lower[0] = s + 1
            lower[1] = 1
    else:
        if j == 0:
            lower[0] = s - 1
            lower[1] = 3
        elif j == 2:
            lower[0] = s - 1
            lower[1] = 5
        elif j == 3:
            lower[0] = s + 1
            lower[1] = 0
        elif j == 5:
            lower[0] = s + 1
            lower[1] = 2
    return lower

def get_int(a):
    b = int(a)
    if a - b < 0.5:
        return b
    else:
        return b + 1

def main():
    print(is_lower(0, 3))
    # 1. Create a model
    m = gp.Model("CICO_" + str(step))

    # 2. Create variables
    e = m.addVars(step * 2, lb = 0, ub = e_max, vtype = GRB.INTEGER, name = "e") # 记录方程次数的变量，每个线性结构中最多引入两个方程
    d = m.addVars(step * 6, lb = 0, ub = d_max, vtype = GRB.INTEGER, name = "d") # 每个位置作为先有变量表达式的次数
    v = m.addVars(step * 6, lb = 0, ub = 1, vtype = GRB.BINARY, name = "v") # 是否引入未知数变量
    c = m.addVars(step * 6, lb = 0, ub = 1, vtype = GRB.BINARY, name = "c") # 是否引入常数变量
    b = m.addVars(step * 6, lb = 0, ub = 1, vtype = GRB.BINARY, name = "b") # 是否选为基
    g = m.addVars(step * 6, lb = 0, ub = 1, vtype = GRB.BINARY, name = "g") # 是否消耗自由度
    h = m.addVars(step * 6, lb = 0, ub = 1, vtype = GRB.BINARY, name = "h") # 用于标记消耗了自由度但没有选入基的位置

    # 3. Post constraints
    # 3.1 一些很显然的约束
    # 已知两个位置是常数
    m.addConstr(c[0 * 6 + 1] == 1)
    m.addConstr(c[(step - 1) * 6 + 5] == 1)
    # 已知第一个状态引入变量，第三个状态与第一个状态为线性关系
    m.addConstr(v[0 * 6 + 0] == 1)
    m.addConstr(c[0 * 6 + 2] == 1)

    tmp = 0
    for i in range(len(c)):
        tmp = tmp + c[i]
    m.addConstr(tmp == 3) # 只能有三个常数变量
    tmp = 0
    for i in range(len(v)):
        tmp = tmp + v[i]
    m.addConstr(tmp >= 1) # 至少引入一个变量
    m.addConstr(tmp == v_num) # 变量个数

    # 设定方程个数等于变量个数
    sum_v = 0
    sum_g = 0
    for i in range(len(v)):
        sum_v = sum_v + v[i]
    for i in range(len(g)):
        sum_g = sum_g + g[i]
    m.addConstr(sum_g - 3 * step == sum_v)

    # 方程次数之和变量
    e_sum = m.addVar(lb = 0, ub = e_sum_max, vtype = GRB.INTEGER) # 方程次数之和，设置目标函数用，初始化
    tmp = 0
    for i in range(len(e)):
        tmp = tmp + e[i]
    m.addConstr(tmp == e_sum) # 方程次数之和，设置目标函数用，定义

    # 一些显而易见的约束
    for i in range(step):
        for j in range(6):
            m.addConstr((c[i * 6 + j] == 1) >> (d[i * 6 + j] == 0)) # 常数变量次数一定为0
            d_tmp = m.addVar(lb = 0, ub = 1, vtype = GRB.BINARY)
            m.addConstr(d_tmp >= d[i * 6 + j] / d_max)
            m.addConstr(d_tmp <= d[i * 6 + j])
            m.addConstr((d_tmp == 0) >> (g[i * 6 + j] == 1)) # 常数一定确定一个自由度
            m.addConstr((v[i * 6 + j] == 1) >> (g[i * 6 + j] == 1)) # 新引入变量一定确定一个自由度
            m.addConstr((v[i * 6 + j] == 1) >> (d[i * 6 + j] == 1)) # 新引入变量的位置次数为1
            m.addConstr((d_tmp == 0) >> (b[i * 6 + j] == 1)) # 常数变量一定作为基
            m.addConstr((d_tmp == 0) >> (v[i * 6 + j] == 0)) # 常数变量一定不会引入新变量
            m.addConstr((b[i * 6 + j] == 1) >> (g[i * 6 + j] == 1)) # 基变量只能从确定了自由度的位置取，即确定了自由度的位置去表达其他的位置
            # g=1 但 b=0 的位置就是次数次高的位置，用h=1标记
            tmp = m.addVar(lb = 0, ub = 1, vtype = GRB.BINARY)
            tmp_ = m.addVar(lb = 0, ub = 1, vtype = GRB.BINARY)
            m.addConstr(tmp_ == 1 - b[i * 6 + j])
            m.addGenConstrAnd(tmp, [g[i * 6 + j], tmp_])
            m.addConstr((tmp == 1) >> (h[i * 6 + j] == 1))
            m.addConstr((h[i * 6 + j] == 1) >> (tmp == 1))

    # 一个线性结构体内部，关于确定的自由度个数、基的个数的设定
    for i in range(step):
        sum_g = 0
        sum_b = 0
        for j in range(6):
            sum_g = sum_g + g[i * 6 + j]
            sum_b = sum_b + b[i * 6 + j]
        m.addConstr(sum_g >= 3)
        #m.addConstr(sum_g <= 5)
        m.addConstr(sum_b == 3)

    # 3.2 结构体内部自由度确定的位置次数怎样设定，基变量选取自由度确定的位置中次数最小的3个，h标记自由度确定、且没有被选为基的位置，需要由基表达的位置的次数等于基位置的最大次数
    max_in_bd = m.addVars(step, lb = 0, ub = e_sum_max, name = "max_in_bd") # 每个结构体中每个位置的基变量乘以次数变量的最大值
    max_in_gd = m.addVars(step, lb = 0, ub = e_sum_max, name = "max_in_gd") # 每个结构体中每个位置的自由度变量乘以次数变量的最大值
    hd_sum = m.addVars(step, lb = 0, ub = e_sum_max, name = "hd")
    g_sum = m.addVars(step, lb = 0, ub = 6, name = "g_sum")

    for i in range(step):
        bd_inL = m.addVars(6, vtype = GRB.INTEGER)  # 每个位置 b * d
        gd_inL = m.addVars(6, vtype = GRB.INTEGER)  # 每个位置 g * d
        hd_list = m.addVars(6, vtype = GRB.INTEGER)   # 每个位置 h * d
        g_list = m.addVars(6, vtype = GRB.BINARY)
        for j in range(6):
            m.addQConstr(bd_inL[j] - b[i * 6 + j] * d[i * 6 + j] <= 0.5)
            m.addQConstr(bd_inL[j] - b[i * 6 + j] * d[i * 6 + j] >= -0.5)
            m.addQConstr(gd_inL[j] - g[i * 6 + j] * d[i * 6 + j] <= 0.5)
            m.addQConstr(gd_inL[j] - g[i * 6 + j] * d[i * 6 + j] >= -0.5)
            m.addQConstr(hd_list[j] - h[i * 6 + j] * d[i * 6 + j] <= 0.5)
            m.addQConstr(hd_list[j] - h[i * 6 + j] * d[i * 6 + j] >= -0.5)
            m.addConstr(g_list[j] == g[i * 6 + j])
            continue
        m.addGenConstrMax(max_in_bd[i], bd_inL)
        m.addGenConstrMax(max_in_gd[i], gd_inL)
        tmp = 0
        for j in range(len(hd_list)):
            tmp = tmp + hd_list[j]
        m.addConstr(tmp == hd_sum[i])


        for j in range(6):
            if (i == 0 and j == 0) or (i == 0 and j == 2):
                m.addConstr(g[i * 6 + j] == 1)
                m.addConstr(b[i * 6 + j] == 1)
            elif i == 0 and j == 1:
                m.addConstr(g[i * 6 + j] == 1)
                m.addConstr(b[i * 6 + j] == 1)
                m.addConstr(d[i * 6 + j] == 0)
            elif (i == step - 1 and j == 3) or (i == step - 1 and j == 4):
                m.addConstr(g[i * 6 + j] == 0)
            elif i == step - 1 and j == 5:
                continue
            else: # 非边缘位置
                tmp_or = m.addVar(0, 1, vtype = GRB.BINARY)
                if is_lower(i, j) == False: # 上游位置
                    lower = get_lower(i, j)
                    m.addGenConstrOr(tmp_or, [c[i * 6 + j], c[lower[0] * 6 + lower[1]]])
                    m.addConstr((g[i * 6 + j] == 0) >> (d[i * 6 + j] == max_in_bd[i])) # 当前位置若是被表达的位置，则其次数由所在结构基位置的次数决定
                    # 上游位置若消耗了自由度，当且仅当引入了新变量或为常数
                    tmp = m.addVar(lb = 0, ub = 1, vtype = GRB.BINARY, name = "tmp" + str(i + 1) + str(j + 1))
                    tmp_ = m.addVar(lb = 0, ub = 1, vtype = GRB.BINARY, name = "tmp_" + str(i + 1) + str(j + 1))
                    m.addConstr(tmp_ >= 1 - d[i * 6 + j])
                    m.addConstr(tmp_ <= 1 - d[i * 6 + j] / d_max)
                    m.addGenConstrOr(tmp, [tmp_, v[i * 6 + j]])
                    m.addConstr((g[i * 6 + j] == 1) >> (tmp == 1))
                    m.addConstr((tmp == 1) >> (g[i * 6 + j] == 1))
                else: # 对下游位置
                    upper = get_upper(i, j)
                    m.addGenConstrOr(tmp_or, [c[i * 6 + j], c[upper[0] * 6 + upper[1]]])
                    m.addConstr(g[i * 6 + j] == 1) # 下游位置都引入自由度
                    #m.addConstr((v[i * 6 + j] == 0) >> (d[i * 6 + j] == d[upper[0] * 6 + upper[1]] * 3))
                    m.addConstr(d[i * 6 + j] == d[upper[0] * 6 + upper[1]] * 3) # 下游节点的次数等于上游节点的次数*3

        # 根据结构体内部确定的自由度的个数设定方程的次数
        # 结构体内确定3个自由度时，不引入方程
        tmp = 0
        for j in range(len(g_list)):
            tmp = tmp + g_list[j]
        m.addConstr(tmp == g_sum[i])
        tmp3 = m.addVar(lb = 0, ub = 1, vtype = GRB.BINARY)
        tmp4 = m.addVar(lb = 0, ub = 1, vtype = GRB.BINARY)
        tmp5 = m.addVar(lb = 0, ub = 1, vtype = GRB.BINARY)
        tmp6 = m.addVar(lb = 0, ub = 1, vtype = GRB.BINARY)
        m.addConstr(3 * tmp3 + 4 * tmp4 + 5 * tmp5 + 6 * tmp6 == g_sum[i])
        m.addConstr((tmp3 == 1) >> (e[i * 2 + 0] == 0))
        m.addConstr((tmp3 == 1) >> (e[i * 2 + 1] == 0))

        # 结构体内确定4个自由度时，引入一个方程
        m.addConstr((tmp4 == 1) >> (e[i * 2 + 0] == max_in_gd[i]))
        m.addConstr((tmp4 == 1) >> (e[i * 2 + 1] == 0))

        # 结构体内确定5个自由度时，引入两个个方程
        m.addConstr((tmp5 == 1) >> (e[i * 2 + 0] == max_in_gd[i]))
        m.addConstr((tmp5 == 1) >> (e[i * 2 + 1] == hd_sum[i] - max_in_gd[i])) # 需要减掉最高次才是次高次

        # 结构体内确定6个自由度时，引入三个个方程
        m.addConstr((tmp6 == 1) >> (e[i * 2 + 0] == max_in_gd[i]))
        m.addConstr((tmp6 == 1) >> (e[i * 2 + 1] == hd_sum[i] - max_in_gd[i])) # 需要减掉最高次才是次高次


        # 只有加入下面这组条件才能保证基变量b_j在次数小的位置取1，h_j变量在次数大的位置取1
        for j in range(6):
            m.addConstr((h[i * 6 + j] == 1) >> (hd_list[j] >= bd_inL[0]))
            m.addConstr((h[i * 6 + j] == 1) >> (hd_list[j] >= bd_inL[1]))
            m.addConstr((h[i * 6 + j] == 1) >> (hd_list[j] >= bd_inL[2]))
            m.addConstr((h[i * 6 + j] == 1) >> (hd_list[j] >= bd_inL[3]))
            m.addConstr((h[i * 6 + j] == 1) >> (hd_list[j] >= bd_inL[4]))
            m.addConstr((h[i * 6 + j] == 1) >> (hd_list[j] >= bd_inL[5]))
            continue

    # 4. Solve the problem
    #m.setObjective(tmp, GRB.MINIMIZE)
    m.setObjective(e_sum, GRB.MINIMIZE)
    m.Params.MIPGap = 0
    m.write("CICO_" + str(step) + ".lp")
    m.optimize()
    if m.Status != GRB.OPTIMAL:
        print("无解")
    else:
        m.write("CICO_" + str(step + 1) + ".sol")
        for s in range(step):
            print("g" + str(s + 1) + "_123 =", 1 if g[s * 6 + 0].X > 0.5 else 0, 1 if g[s * 6 + 1].X > 0.5 else 0, 1 if g[s * 6 + 2].X > 0.5 else 0)
            print("b" + str(s + 1) + "_123 =", 1 if b[s * 6 + 0].X > 0.5 else 0, 1 if b[s * 6 + 1].X > 0.5 else 0, 1 if b[s * 6 + 2].X > 0.5 else 0)
            print("h" + str(s + 1) + "_123 =", 1 if h[s * 6 + 0].X > 0.5 else 0, 1 if h[s * 6 + 1].X > 0.5 else 0, 1 if h[s * 6 + 2].X > 0.5 else 0)
            print("v" + str(s + 1) + "_123 =", 1 if v[s * 6 + 0].X > 0.5 else 0, 1 if v[s * 6 + 1].X > 0.5 else 0, 1 if v[s * 6 + 2].X > 0.5 else 0)
            print("d" + str(s + 1) + "_123 =", get_int(d[s * 6 + 0].X), get_int(d[s * 6 + 1].X), get_int(d[s * 6 + 2].X))
            print("e" + str(s + 1) + "_12 =", get_int(e[s * 2 + 0].X), get_int(e[s * 2 + 1].X))
            print("g" + str(s + 1) + "_456 =", 1 if g[s * 6 + 3].X > 0.5 else 0, 1 if g[s * 6 + 4].X > 0.5 else 0, 1 if g[s * 6 + 5].X > 0.5 else 0)
            print("b" + str(s + 1) + "_456 =", 1 if b[s * 6 + 3].X > 0.5 else 0, 1 if b[s * 6 + 4].X > 0.5 else 0, 1 if b[s * 6 + 5].X > 0.5 else 0)
            print("h" + str(s + 1) + "_456 =", 1 if h[s * 6 + 3].X > 0.5 else 0, 1 if h[s * 6 + 4].X > 0.5 else 0, 1 if h[s * 6 + 5].X > 0.5 else 0)
            print("v" + str(s + 1) + "_456 =", 1 if v[s * 6 + 3].X > 0.5 else 0, 1 if v[s * 6 + 4].X > 0.5 else 0, 1 if v[s * 6 + 5].X > 0.5 else 0)
            print("d" + str(s + 1) + "_456 =", get_int(d[s * 6 + 3].X), get_int(d[s * 6 + 4].X), get_int(d[s * 6 + 5].X))
            print("-------------------------------")
        print("current solution found: ", get_int(e_sum.X))

if __name__ == '__main__':
    main()
