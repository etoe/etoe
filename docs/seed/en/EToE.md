---
title: "Ether Theory of Everything"
description: "Foundational seed document defining the core postulates, open questions, and collaboration rules for the EToE project."
language: en
version: 0.1.1
date: 2026-06-11
created: 2026-06-01
updated: 2026-06-11
status: active
priority: critical
audience: LLM, Human
type: seed
tags: [toe, grand-unified-theory, quantum-gravity, open-science]
authors: ["EToE-Project Team"]
license: "Apache-2.0"
---        
Ether Theory of Everything is a Theory of Everything based on corrected and refined concepts of the luminiferous ether, gravitating ether, atom, light, electric current, physical fields, and other physical concepts, as well as the origin of life, consciousness, and society.

Ether is a synonym for the physical theory of the philosophical concept of "matter". Sometimes in the English version, "ether" is "aether" or "æther".

The capital letter Æ is used for the initial letter of abbreviations of names related to modern ether science.

In the English version, the abbreviation for "Ether Theory of Everything" is "ÆToE".

Ether Theory of Everything includes "Ether Theory of Matter", "Ether Theory of Life", "Ether Theory of Consciousness," and "Ether Theory of Society". In the English version, the abbreviation for "Ether Theory of Matter" is "ÆToM". In English, the abbreviation for "Ether Theory of Life" is "ÆToL". In the English version, the abbreviation for "Ether Theory of Consciousness" is "ÆToC". In the English version, the abbreviation for "Ether Theory of Society" is "ÆToS".

Ether Theory of Everything is based on the philosophy of "Evolutionary Ether Materialism". In the English version, the abbreviation for "Evolutionary Ether Materialism" is "EÆM".

Next is a brief summary of the Ether Theory of Matter.

Ether Theory of Matter is built on the concept of transparent inertial ether.

The concept of transparent inertial ether is based on the idea that discrete absolute matter exists in discrete Euclidean  three-dimensional absolute space and in discrete absolute time. The philosophy of evolutionary ether materialism stems from the idea that full evolution of matter is possible only in three-dimensional space, as two-dimensional space is too little for the evolution of matter, and four-dimensional space is too much.

All ether in all space and time can be conventionally called "space-time-ether". In English, the abbreviation for "space-time-ether" is "STÆ".

Ether Theory of Matter uses the "Ether System of Units". In the English version, the abbreviation for "Ether System of Units" is "ÆSoU".

The unit of measurement of discrete quantity in the ether system of units is "æn". The reference discrete quantity is expressed by an even natural number and is denoted by $N_Æ$. When modeling for a 64-bit signed integer data type, the maximum $N_Æ$ is two to the sixty-third power: $N_Æ=2^{63}$. For a 32-bit signed integer data type, the maximum $N_Æ$ is two to the thirty-first power: $N_Æ=2^{31}$. For a 16-bit signed integer data type, the maximum $N_Æ$ is two to the fifteenth power: $N_Æ=2^{15}$:

$$
N_{Æ} \in 2\mathbb{Z}^{+} 
$$

$$
N_{Æ} = 2^{n}
$$

The space $S_Æ$ consists of identical "cells".

The unit of measurement for the number of space cells in the ether system of units is "æс".

The number of cells in the space can be finite. In the case of a finite space, the overflow of the absolute space coordinate does not affect physical laws. In the simplest model, the "number of cells in the space on each coordinate axis" $L_Æ$ is equal to the "standard discrete quantity" $N_Æ$. The space $S_Æ$ is a three-dimensional integer lattice with a toroidal topology:

$$
L_{Æ} = N_{Æ}
$$

$$
S_{Æ} = \left\lbrace (x, y, z) \in \mathbb{Z}^3 \mid -\frac{L_{Æ}}{2} \le x, y, z \lt \frac{L_{Æ}}{2} \right\rbrace
$$

"Space wrapping function" $WS_Æ(n)$, which maps any integer $n$ into the interval $[ -L_Æ/2, L_Æ/2 - 1 )$ taking into account the cyclic nature of the space:

$$
WS_{Æ}(n) = \left( n + \frac{L_{Æ}}{2} \right)\pmod{L_{Æ}} - \frac{L_{Æ}}{2}
$$

The unit of measurement of the extent of space in the ether system of units is "æl". The size of a space cell is 1 æl:

$$l_æ = 1 æl$$

The unit of measurement of the volume of space in the ether system of units is "æs".

The reference distance is denoted by $D_Æ$. In the simplest model, the reference distance is one less than the reference quantity:

$$D_Æ = N_Æ -1$$

The coordinate of absolute position ($p_A$) in absolute space has a range from $-L_Æ/2$ to $L_Æ/2-1$. The coordinate of relative position ($p_R$) in absolute space has a range from $-D_Æ$ to $D_Æ$:

$$p_A = (x, y, z) \in \mathbb{Z}^3 \mid -\frac{L_Æ}{2} \le x, y, z \le \frac{L_Æ}{2} $$

$$p_R = (x, y, z) \in \mathbb{Z}^3 \mid  -D_Æ \le x, y, z \le D_Æ$$

$V_Æ$ is the discrete volume of the entire space. Formula for the discrete volume of the entire space:

$$V_Æ = L_Æ \cdot L_Æ \cdot L_Æ$$

Neighboring cells are considered to be the nearest orthogonal cells. In the simplest model, the nearest diagonal cells are not considered neighboring cells. This definition of neighboring cells can be argued by the absence of diagonal cells in one-dimensional space.

Time is divided into equal ticks.

The number of time ticks can be finite. In the case of finite time, the overflow of the absolute time counter does not affect physical laws.

The unit of measurement for time in the ether system of units is "æt".

$T_Æ$ is the discrete size of all time. In the simplest model, the discrete size of all time is equal to the "standard discrete quantity" $N_Æ$. Therefore, in the simplest model, the discrete size of all time is equal to the discrete size of all space:

$$T_Æ=N_Æ$$

$$T_Æ=L_Æ$$

$T_Æ=L_Æ$ is a conditional formula for the principle of numerical equivalence of all time and the size of all space.

The current time tick is denoted by $t_Æ$. Time ticks are numbered from $0$ to $T_Æ-1$. The tick with the number $0$ is called the "zero tick". The zero tick at the "start of time" is called the "start tick". After the tick with the number $T_Æ-1$, there is another tick with the number $0$. The "time wrapping function" $WT_{Æ}(n)$, which maps any integer $n$ to the interval $[ 0, T_Æ)$, taking into account the cyclic nature of time:

$$WT_{Æ}(n) = \left( n \right)\pmod{T_Æ}$$

$$t_Æ = WT_{Æ}(t_Æ+1)$$

Each ether object is conventionally assigned to one of eight levels of matter. For brevity, the level of matter can be denoted by the capital letter $Æ$ with a number corresponding to the level of matter. Æ1 is the designation for the first level of matter, Æ2 for the second, Æ3 for the third, Æ4 for the fourth, Æ5 for the fifth, Æ6 for the sixth, Æ7 for the seventh, Æ8 for the eighth.

Etheron is the name of a discrete particle of matter at the first level of matter. Etheron is considered an ether object of the first level of matter. Etheron is denoted by the sign $æ$. In formulas, a separate sign $æ$ denotes one etheron from the set of all etherons.

Ether is etherons. Ether is denoted by the symbol $Æ$. In the formulas, the separate sign $Æ$ denotes the set of all etherons.

Ether objects of the second and subsequent levels of matter are called "ether hyperobjects".

In ether theory, the prefix "hyper" for any physical object or any informational object means "non-elementarity" of this object. Non-elementarity of an object of any type means that the object consists of subobjects of the same type.

In ether theory, the prefix "sub" for any physical object or any informational object means "nestedness" of this object in an object of a higher level. Nestedness of an object of any type means that the object is a component part of an object of the same type but of a higher level.

Subobjects of ether hyperobjects are called "ether subobjects". In the English version, "ether subobject" is "ether subobject".

Ether subobjects of ether objects of the second level of matter are etherons.

An ether subobject containing ether subobjects of a lower level is called "ether subhyperobject".

An etheron that is not a subobject of any ether hyperobject is called "medium etheron".

"Ether medium" is medium etherons.

The spatial, temporal, and velocity parameters of the ether medium constitute the configuration of the ether medium.

The configuration of the ether medium depends on ether hyperobjects.

An etheron that is not a subobject of a given ether hyperobject is called "external etheron" for this ether hyperobject.

"External ether" for an ether hyperobject is external etherons.

The external ether for an ether hyperobject includes all etherons of the ether medium and all etherons of all other ether hyperobjects, except for the etherons of this ether object.

The concept of "ether medium" and the concept of "external ether" are not synonyms. The concept of "external ether" is specific to each ether hyperobject.

The spatial, temporal, and velocity parameters of the external ether constitute the configuration of the external ether for the ether hyperobject.

The total number of etherons in space does not change.

Mass is the number of etherons.

The unit of measurement for mass in the ether system of units is "æm".

$m_Æ$ is the discrete mass of the entire ether, measured in æm.

$ρ_Æ$ is the discrete density of ether, measured in æm/æs and equal to the ratio of the discrete mass of ether $m_Æ$ to the discrete volume of space $V_Æ$: 

$$ρ_Æ=m_Æ/V_Æ$$

The mass of an etheron is 1 æm.

In the simplest version, the total number of etherons in the Universe is equal to the number of cells of absolute space in the Universe. In the case of equality of the amounts of matter and space, the discrete density of the Universe's ether is equal to unity: $ρ_Æ=m_Æ/V_Æ=1$. Therefore, with equality of the amounts of matter and space in the Universe, the discrete mass of ether in the Universe is equal to the discrete volume of the Universe: $m_Æ=V_Æ$. The equality of the quantities of matter and space in the Universe is called the "principle of numerical equivalence of matter and space".

Hypothetically, the "initial" Universe could have space with one etheron in each cell.

It is likely that if, with the existing amount of motion of matter, the amount of matter were "significantly less" or "significantly more" than the amount of space, then full evolution of matter in the Universe would be impossible.

Several etherons can be in one space cell at the same time. A space cell in which there is one etheron or several etherons at a given time tick is called an "occupied cell".

Several etherons can interact simultaneously in one cell of space. The interaction of etherons can be conventionally called "collision of etherons".

In one space cell, interacting etherons and etherons that do not interact with the interacting etherons can be present simultaneously.

A space cell may have no etherons for some time. A space cell in which there are no etherons at a given time tick is called an "empty cell".

Ether is called transparent due to the possibility of several etherons being in one space cell at the same time.

If an etheron is depicted as occupying the entire cell of absolute space, then in the image, oncoming etherons will pass through each other.

Each etheron stores information about its state and about the parameters determining the position and motion of the etheron in space. In computer simulation programs of transparent inertial ether, information related to the etheron may include additional data that speeds up the simulation process and simplifies the simulation logic. In optimized computer simulations of space-time-ether models, it is preferable to use the "structure of arrays" (SoA) scheme to accommodate information about etherons.

The parameters of an etheron can change upon interaction with other etherons that are in the same space cell as the etheron itself.

The "state" of an etheron is denoted by $s_æ$. Each etheron can be in one of four states:

$$s_æ \in \{1, 2, 3, 4\}$$

Ether is called multistate because etherons are in different states.

In the simplest STÆ model, each state of an etheron lasts for at least one time tick and is processed only once during the current time tick. Therefore, in general, in a computer simulation, each etheron may need a "counter of ticks of the time an etheron is in its state" - $t_æ$, as well as a "flag for processing the current state in the current time tick" - $f_æ$. At the beginning of each time tick, the flags of all etherons are reset to zero, and after processing ($F_æ$) in the current time tick ($t_Æ$) by an etheron of its state, the etheron's flag is set to one, and the etheron can no longer process its state in the current time tick again:

$$\forall æ \quad f_{æ}^{(t_Æ+1)} = 0$$

$$f_{æ}^{(t_Æ)} = \Phi(\, f_{æ}^{(t_Æ)} \lor F_{æ}^{(t_Æ)} \,)$$

The first state of the etheron is the "rest of the etheron" in the cell of space. The first state of the etheron is designated $s1_æ$. The duration of the first state of the etheron is denoted by $τ1_æ$. The duration of the first state of the etheron is at least one tick of time:

$$τ1_æ \ge 1$$

The first tick in the "rest" state is conventionally called the "tick of the basic delay". The duration of the "basic delay" of the etheron is denoted by $τ1b_æ$:

$$τ1b_æ \ge 1$$

If the etheron spontaneously remains in the first state for one more tick when it should have passed to the third state, then such a tick is conventionally called the "tick of the spontaneous delay". The duration of the "spontaneous delay" of the etheron is denoted by $τ1r_æ$:

$$τ1r_æ \ge 0$$

If the etheron remains in the first state for one more tick to compensate for the deficit of jumps in the direction of its continuous movement, then such a tick is conventionally called the "tick of the compensatory delay". The duration of the "compensatory delay" of the etheron is denoted by $τ1c_æ$:

$$τ1c_æ \ge 0$$

If the etheron remains in the first state for one more tick to implement a decrease in the continuous speed in the direction of its continuous movement in accordance with the fifth parameter of the etheron, then such a tick is called the "tick of the additional delay". The duration of the "additional delay" of the etheron is denoted by $τ1a_æ$:

$$τ1a_æ \ge 0$$

The duration of the first state of the etheron consists of the duration of the "basic delay", the duration of the "compensatory delay", the duration of the "additional delay" and the duration of the "spontaneous delay": 

$$τ1_æ = τ1b_æ + τ1c_æ + τ1a_æ + τ1r_æ$$

The second state of the etheron is the "interaction of the etheron" in a cell of space with other etherons located in the same cell. The second state of the etheron is denoted $s2_æ$.The etheron always passes into the second state from the first state if there are other etherons in the first state in the cell of space. The duration of the second state of the etheron is denoted by $τ2_æ$. The duration of the second state of the etheron is at least one tick of time:

$$τ2_æ \ge 1$$

The third state of an etheron is "movement from the cell" in which the etheron is located. The third state of an etheron can be called "the departure of an etheron". The third state of the etheron is denoted $s3_æ$. An etheron usually moves to the third state from the first state if there are no other etherons in the first state in the space cell, and if a time tick has arrived in which, in accordance with the parameters of the etheron's movement, it is necessary to move from the space cell. But sometimes an etheron can spontaneously remain in the first state for another time tick, even if it should have moved to the third state. If an etheron spontaneously remains in the first state, then when other etherons appear in the cell, the etheron will move to the second state, not to the third state. An etheron also moves to the third state from the second state. The duration of the third state of the etheron is denoted by $τ3_æ$. The duration of the third state of an etheron is at least one tick of time:

$$τ3_æ \ge 1$$

The fourth state of the etheron is "movement to the neighboring cell" that corresponds to the parameters of the etheron's movement, and in which the etheron will be. The fourth state of the etheron is called "arrival of the etheron". The fourth state of the etheron is denoted $s4_æ$. The etheron moves to the fourth state from the third state. The etheron moves to the first state from the fourth state. The duration of the fourth state of the etheron is denoted by $τ4_æ$. The duration of the fourth state of the etheron is at least one tick of time:

$$τ4_æ \ge 1$$

The third state of the etheron and the fourth state of the etheron together constitute the "etheron jump" from the cell in which the etheron is located to the neighboring cell in which the etheron will be located, in accordance with the parameters of the etheron's movement. The duration of the etheron jump is denoted by $τj_æ$. The duration of the etheron jump is at least two time ticks:

$$τj_æ = τ3_æ + τ4_æ$$

$$τj_æ \ge 2$$

The duration of the basic delay of the etheron in the resting state $τ1b_æ$ together with the duration of the etheron jump $τj_æ$ make up the basic duration of the etheron movement $τb_æ$. The basic duration of the etheron movement is at least three ticks of time: 

$$τb_æ = τ1b_æ + τ3_æ + τ4_æ = τ1b_æ + τj_æ$$

$$τb_æ \ge 3$$

The relative number of time ticks after which an etheron, which is in a state of rest at a given time tick, will be in the next cell of space in a state of rest is called the duration of the etheron step $τs_æ$: 

$$τs_æ = 1 + τ3_æ + τ4_æ = 1 + τj_æ$$

The cycle of an etheron is a sequence of states starting with the first state and ending with the fourth state. The duration of the etheron cycle is denoted by $τ_æ$.

An etheron cycle without the second state of the etheron is called a "free cycle". The duration of the free cycle of etheron is denoted by $τf_æ$. The duration of the free cycle of etheron is made up of the duration of the first state, the duration of the third state, and the duration of the fourth state: 

$$τf_æ = τ1_æ + τ3_æ + τ4_æ$$

$$τf_æ \ge 3$$

An etheron cycle with the second state of the etheron is called a "collisional cycle". The duration of the collision cycle of the etheron is denoted by $τc_æ$. The duration of the collision cycle of the etheron is made up of the duration of the first state, the duration of the second state, the duration of the third state, and the duration of the fourth state: 

$$τc_æ = τ1_æ + τ2_æ + τ3_æ + τ4_æ$$

$$τc_æ \ge 4$$

Velocity relative to absolute space is called "absolute velocity".

The unit of measurement for velocity in the ether system of units is "æv".

The kinematic displacement of an etheron from a cell to an adjacent cell is called "jump displacement". The speed of the jump displacement is called "jump velocity".

Free motion of an etheron is a sequence of states starting after the state of interaction with other etherons and ending before the state of interaction with other etherons.

The cell of space in which the etheron was located when interacting with other etherons is called the "initial cell" of free motion.

The jump of the etheron after interacting with other etherons is called the "initial jump" of free motion.

The jump of the etheron before interacting with other etherons is called the "final jump" of free motion.

The cell of space in which the etheron was located before interacting with other etherons is called the "final cell" of free motion.

The final cell of the previous free motion is the initial cell of the next free motion.

The trajectory of the jumps of the etheron through the cells of space from the initial jump of free motion to the final jump of free motion is called a "free discrete path". The free discrete path begins in the initial cell of free motion and ends in the final cell of free motion. The free discrete path is a discrete approximation of a straight line. The average speed of an etheron along a free discrete path is called the "discrete speed".

The kinematic displacement of the etheron from the initial cell of free motion to the final cell of free motion is called "continuous displacement". The speed of continuous displacement is called "continuous velocity".

The continuous velocity of an etheron is a discrete approximation of constant velocity.

An etheron is called inertial due to the conditionally rectilinear and conditionally uniform free motion of the etheron.

Ether is called inertial due to the conditionally rectilinear and conditionally uniform free motion of etherons.

The average absolute continuous speed of an etheron is denoted by the capital Latin letter $C$.

Absolute continuous speeds of an etheron can only be in a narrow range around $C$. An etheron with an absolute continuous speed below $C$ is considered "low-speed". An etheron with an absolute continuous speed above $C$ is considered "high-speed".

A freely moving etheron is considered an inertial reference frame.

Continuous velocity relative to an inertial reference frame is called "relative velocity".

Transformations of coordinates and continuous velocity of an etheron or group of etherons when transitioning in the description of their motion from one inertial reference frame to another correspond to Galilean transformations.

The first parameter of an etheron is the absolute position of the cell in which the etheron is located at the current time tick. The first parameter of an etheron is called "position". The first parameter of the etheron is denoted by $\vec{r}_æ$. At the starting tick of time in the simplest model, in each cell of space there is one etheron with the first parameter equal to the position of the cell in which this etheron is located.

The second parameter of an etheron is the absolute position of the cell in which the etheron interacted with other etherons once again. The second  parameter of an etheron is called "collision position". The second parameter of the etheron is denoted by $\vec{rc}_æ$. At each zero tick of time in the simplest model, the value from the first parameter of the etheron is entered into the second parameter of the etheron.

The third parameter of an etheron is the absolute time tick in which the etheron interacted with other etherons once again. The third parameter of the etheron is called "collision tick". The third parameter of the etheron is denoted by $tc_æ$. If an etheron spontaneously lingers in the first state for an additional time tick, then the third parameter of an etheron is increased by one. At every zero tick of time in the simplest model, the third parameter of the etheron is reset to zero.

The fourth parameter of an etheron is the relative position of the distant cell to which the etheron moves after interacting with other etherons. The fourth parameter of an etheron is called "direction". The fourth parameter of an etheron is denoted by $\vec{d}_æ$. The fourth parameter of an etheron is the reference direction vector, the coordinates of which have a range from $-D_Æ$ to $D_Æ$, where $D_Æ$ is the reference distance. The length of the reference direction vector is approximately equal to $D_Æ$. The reference direction vector is the vector of displacement by the reference distance $D_Æ$. In the simplest simulator, the random "direction" vector $\vec{d}_æ$ for the etheron can be obtained through angles in a spherical coordinate system:

$$\vec{d}_æ = (D_Æ \cdot \sin\theta \cdot \cos\varphi, D_Æ \cdot \sin\theta \cdot \sin\varphi, D_Æ \cdot \cos\theta)$$

where:
- $\theta \sim U[0, \pi]$ is the zenith angle, uniformly distributed on $[0, \pi]$
- $\varphi \sim U[0, 2\pi]$ is the azimuth angle, uniformly distributed on $[0, 2\pi]$

The fifth parameter of the etheron is the "total additional delay" of the etheron in ticks of time in the "rest" state, with which the etheron, when moving freely, will reach the cell whose position is the sum of the absolute position of the cell specified in the second parameter and the relative position of the cell specified in the fourth parameter. The fifth parameter of the etheron is called "delay". The fifth parameter of the etheron is designated $a_æ$. The letter 'a' in the designation of the fifth parameter of the etheron comes from the English word "addition", since the meaning of "delay" is an addition to some time or an addition to some duration. The fifth parameter of the etheron can be expressed as an unsigned integer from a certain range. In the simplest case, the range of values ​​of the fifth parameter lies from $0$ to $D_Æ$, where $D_Æ$ is the reference distance. In the simplest model, the fifth parameter is the "total additional delay" in the Euclidean free continuous displacement of the etheron over the Euclidean reference distance $D_Æ$. The value of the fifth parameter of the etheron cannot overflow. The zero value of the fifth parameter of the etheron corresponds to the maximum value of the range of absolute continuous velocities of the etheron. And the maximum value of the fifth parameter of the etheron corresponds to the minimum value of the range of absolute continuous velocities of the etheron. The average value of the fifth parameter of the etheron in the simplest model is equal to half of $D_Æ$: 

$$a_{æavg}= \frac{D_Æ}{2}$$

The fifth parameter of the etheron is the "total additional delay" of the etheron in time ticks in the "rest" state, with which the etheron, in free movement, will reach the cell whose position is the sum of the absolute position of the cell specified in the second parameter and the relative position of the cell specified in the fourth parameter. The fifth parameter of the etheron is called the "delay". The fifth parameter of the etheron is denoted by $a_æ$. The fifth parameter of the etheron can be expressed as an unsigned integer from a certain range. In the simplest case, the range of values ​​of the fifth parameter lies from $0$ to $D_Æ$, where $D_Æ$ is the reference distance. In the simplest model, the fifth parameter is the "total additional delay" during the Euclidean free continuous movement of the etheron by the Euclidean reference distance $D_Æ$. The value of the fifth parameter of the etheron cannot overflow. The zero value of the fifth parameter of the etheron corresponds to the maximum value of the range of absolute continuous speeds of the etheron. And the maximum value of the fifth parameter of the etheron corresponds to the minimum value of the range of absolute continuous speeds of the etheron.

In the simplest model, copying the "position" parameter ( $\vec{r}$<sub>æ</sub> ) of each etheron into the "collision position" parameter ( $\vec{rc}$<sub>æ</sub> ) of that etheron and zeroing the "collision tick" parameter ( $tc_{æ}$ ) of each etheron at every zero tick of time ( $t_Æ=0$ ) prevents uncertainty in the time elapsed since collisions:

$$\forall æ \quad \vec{rc}_{æ}^{(t_Æ=0)} = \vec{r}_{æ}$$

$$\forall æ \quad tc_{æ}^{(t_Æ=0)} = 0$$

In the fourth state of the etheron, the absolute position of the space cell to which the etheron has arrived is entered into the first parameter of this etheron.

The free motion of an etheron is always calculated based on the current time tick and all the parameters of the etheron. Knowing the space cell of the last collision and the time tick of the last collision in which the etheron participated, as well as knowing the relative direction and the total additional delay, it is always possible to determine where the etheron should be at a certain time tick so that the trajectory and velocity of the etheron in free motion are a discrete approximation of uniform and rectilinear motion. The calculation of uniform free motion can be made based on the number of jumps from the space cell of the last collision to the conditional target cell, to which the direction of the etheron points. The number of jumps to the target cell, given the orthogonality of the etheron's jumps, is equal to the "Manhattan distance" to this cell. In the simplest model, for an etheron that is alone in the "rest" state in a certain cell at a given time tick, the position in space is calculated, to which this etheron should reach in accordance with the etheron's motion parameters in the time required for the etheron to jump. If the calculated position in space does not coincide with the current cell of the etheron, then this means that the time tick for this etheron to enter the state of "moving from the cell" has come. If the cell of space into which the etheron must enter is not an adjacent cell, then a three-dimensional version of the Bresenham algorithm can be used to calculate the next cell so that the trajectory of orthogonal jumps best approximates a straight line to this cell.

The trajectory of the etheron jumps always approximates a straight line, and the Euclidean speed of movement along this straight line is approximately constant. Etherons with different directions of movement, but with the same "delay" parameters, move with the same Euclidean speed due to a different number of their "compensatory delay ticks" at rest. The number of jumps to the target cell depending on the direction of movement is determined by the "Manhattan distance" to the target cell in this direction. The greater the number of jumps in the direction of movement, the fewer "compensatory delay ticks" at rest. The smaller the number of jumps in the direction of movement, the more "compensatory delay ticks" at rest. Etherons with the same directions of movement, but with different "delay" parameters, with the same number of "compensatory delay ticks" move with different Euclidean speeds due to a different number of "additional delay ticks".

Compensatory delay ticks are necessary to ensure that the total time of movement over the reference Euclidean distance ($D_Æ$) remains constant, regardless of direction. This time is calibrated by the "slowest" direction — the diagonal in space where the number of jumps is maximum. The number of compensatory delay ticks depends on the Manhattan distance for the direction vector $\vec{d_æ} = (d_{æx}, d_{æy}, d_{æz})$ and is calculated by the formula:

$$T_{æc} = τb_æ \cdot (D_Æ\cdot\sqrt{3} - (|d_{æx}| + |d_{æy}| + |d_{æz}|))$$

where:
* $D_Æ$ is the number of cells in one direction.
* $d_{æx}, d_{æy}, d_{æz}$ are the coordinates of the direction vector.
* $D_Æ\cdot\sqrt{3}$ is the approximate maximum Manhattan distance for a vector with Euclidean length $D_Æ$.
* The coefficient $τb_æ$ arises because each etheron cycle takes several ticks of time, and the compensating delay ticks must compensate for the difference in time, not just in the number of jumps.

"Reference ether delay" is the number of time ticks required to perform the maximum number of jumps over the reference Euclidean distance $D_Æ$:

$$τ_Æ = τb_æ \cdot D_Æ \cdot \sqrt{3}$$

The total time ($T_æ$) spent by the etheron on Euclidean motion over a distance of $D_Æ$ is made up of the base time ($T_{æb}$), the time for compensatory delays ($T_{æc}$), and the time for additional delays ($T_{æa}$):

$$T_{æb} = (|d_{æx}| + |d_{æy}| + |d_{æz}|) \cdot τb_æ$$

$$T_{æc} = τb_æ \cdot (D_Æ\cdot\sqrt{3} - (|d_{æx}| + |d_{æy}| + |d_{æz}|))$$

$$T_{æa} = a_æ$$

If we add these components, the terms containing the direction vector $(\lvert d_{\text{æx}}\rvert + \lvert d_{\text{æy}}\rvert + \lvert d_{\text{æz}}\rvert)$ cancel each other out. As a result, the total time is independent of direction: 

$$T_æ = T_{æb} + T_{æc} + T_{æa} = τb_æ  \cdot D_Æ \cdot \sqrt{3} + a_æ = τ_Æ + a_æ$$

The independence of the total time spent by the etheron on Euclidean motion from the Euclidean direction ensures the same Euclidean speed for etherons with the same "delay" parameter, regardless of the trajectory of their jumps.

The absolute position of the etheron in space $\vec{p}_æ$, where at some point in time $t$ the etheron should be located under the condition of its free movement, is calculated on the basis of the total time spent by the etheron on the Euclidean movement over the distance $D_Æ$:

$$\vec{p}_æ(t) = rc_æ + \frac {(t - tc_æ)\cdot \vec{d_æ}} {τ_Æ + a_æ}$$

The number of etherons in the "rest" state ( $s1$<sub>æ</sub> ) in a cell of space with position $\vec{p}$ is denoted by $N_{s1æ}(\vec{p})$ and is expressed through summation over all etherons from the set $Æ$ using the Kronecker delta symbol $\delta$:

$$N_{s1æ}(\vec{p}) = \sum_{æ \in Æ} \delta(\vec{r}_{\text{æ}}, \vec{p}) \cdot \delta(s_{\text{æ}}, 1)$$

The transition of an etheron from the "rest" state ( $s1_æ$ ) to the "moving from the cell" state ( $s3_æ$ ), provided that there are no other etherons in the "rest" state in the cell, occurs if its position in space ( $\vec{r}$<sub>æ</sub> ) at the current time tick ( $t$<sub>Æ</sub> ) does not coincide with the position $\vec{p}$<sub>æ</sub>$(t$<sub>Æ</sub>$)$, where the etheron should be:

$$s_{\text{æ}}^{(1)} \longrightarrow s_{\text{æ}}^{(3)}, \quad \text{for} \quad ( N_{s1æ}(\vec{r}_{\text{æ}}) = 1 ) \land (\vec{r}_{\text{æ}} \neq p_{\text{æ}}(t_{\text{Æ}}))$$

In the "moving out of cell" state ($s3_æ$), the etheron determines which neighboring cell $\vec{p}$<sub>n</sub> it must go to in order to get to the cell $\vec{p}$<sub>t</sub> where it should be. In a computer simulation, an algorithm similar to a digital differential analyzer (DDA) adapted to toroidal space can be used to find the next neighboring cell $\vec{p}$<sub>n</sub> on the way from the current cell $\vec{r}$<sub>æ</sub> to the cell $\vec{p}$<sub>t</sub> where the etheron should be:

$$\vec{r}_æ = (x_æ, y_æ, z_æ) \in S$$

$$\vec{\delta} = \vec{p}_t - \vec{r}_æ = (\delta_x, \delta_y, \delta_z)$$

$$\vec{\delta'} = (W_{\text{Æ}}(\delta_x), W_{\text{Æ}}(\delta_y), W_{\text{Æ}}(\delta_z)) = (\delta'_x, \delta'_y, \delta'_z)$$

$$i_{dom} = \mathop{\text{argmax}}\limits_{i \in \{x, y, z\}} |\delta'_i|$$

$$\vec{e}_x = (1, 0, 0) ; \vec{e}_y = (0, 1, 0) ; \vec{e}_z = (0, 0, 1)$$

$$\Delta\vec{p} = \mathop {\text{sgn}(\delta'_{i_{dom}})} \cdot \vec{e}_{i_{dom}}$$

$$\vec{p}_{n} = (W_{\text{Æ}}(x_æ + \Delta p_x), W_{\text{Æ}}(y_æ + \Delta p_y), W_{\text{Æ}}(z_æ + \Delta p_z))$$

In the state of "moving to a cell" ($s4_æ$), the etheron's "position" parameter $\vec{r}_æ$ becomes equal to the position of the cell $\vec{p}$<sub>n</sub> it arrived at:

$$s_{\text{æ}} = s^{(4)} \implies \vec{r}_{\text{æ}} = \vec{p}_{n}$$

The modulus of the Euclidean continuous velocity of an etheron $v_{\text{æ}} = \lvert \vec{v}_{\text{æ}} \rvert$ is the ratio of the Euclidean distance traveled to the time spent on its passage. The modulus of the maximum continuous velocity of an etheron does not depend on the direction of movement, since the difference in time arising from a different number of jumps is completely compensated by a different number of ticks of the compensatory delay. The modulus of the continuous velocity of an etheron $v_æ$ is determined only by its "delay" parameter $a_æ$.

Formula for the module of continuous velocity of etheron $v_æ$:

$$v_æ = \frac{D_Æ }{ τb_æ \cdot D_Æ\cdot\sqrt{3} + a_æ }=\frac{D_Æ }{ τ_Æ + a_æ }$$

$$a_æ = \frac{D_Æ}{v_æ} - { τb_æ \cdot D_Æ\cdot\sqrt{3}}= \frac{D_Æ}{v_æ} - τ_Æ$$

where:
* $D_Æ$ — reference Euclidean distance.
* $τ_Æ$ — reference ether delay.
* $a_æ$ — etheron parameter that determines the number of ticks of additional delay during Euclidean movement by the reference Euclidean distance.

The unit vector of continuous velocity of the etheron $\hat{v_æ}$, indicating the direction of the vector of continuous velocity of the etheron $\vec{v_æ}$, is equal to the ratio of the reference direction vector $\vec{d_æ}$ to the reference distance $D_Æ$. The formula for the unit vector of continuous velocity of the etheron $\hat{v_æ}$:

$$\hat{v_æ} = \frac{\vec{d_æ}}{D_Æ}$$

The continuous velocity vector of the etheron $\vec{v_æ}$ is equal to the product of the unit continuous velocity vector of the etheron $\hat{v_æ}$ and the modulus of the velocity of the etheron $v_æ$. Formula for the continuous velocity vector of the etheron $\vec{v_æ}$:

$$\vec{v_æ} = \frac{\vec{d_æ}}{D_Æ} \cdot v_æ = \frac{\vec{d_æ}}{D_Æ} \cdot \frac{D_Æ }{ τ_Æ + a_æ }  = \frac{\vec{d_æ}} { τ_Æ + a_æ }= \frac{\vec{d_æ}} { τb_æ \cdot D_Æ\cdot\sqrt{3} + a_æ }$$

$$\vec{d_æ} = \frac{\vec{v_æ}\cdot D_Æ}{|\vec{v_æ}|}$$

The modulus of the continuous velocity of the etheron $v_æ$ is maximum at the minimum value of the "delay" parameter ($a_æ=0$):

$$v_{æmax} = \frac{D_Æ }{ τb_æ \cdot D_Æ\cdot\sqrt{3}} = \frac{1}{ τb_æ\cdot\sqrt{3}}$$

The modulus of the continuous velocity of the etheron $v_æ$ is minimal at the maximum value of the "delay" parameter ($a_æ=D_Æ$):

$$v_{æmin} = \frac{D_Æ }{ τb_æ \cdot D_Æ\cdot\sqrt{3} + D_Æ}= \frac{1}{ τb_æ\cdot\sqrt{3}+1}$$

The average value of the modulus of the continuous velocity of the etheron occurs at the average value of the "delay" parameter ($a_æ=\frac{D_Æ}{2}$):

$${v_{æavg}} = \frac{D_Æ }{ τb_æ \cdot D_Æ\cdot\sqrt{3} + \frac{D_Æ}{2}}= \frac{1}{ τb_æ\cdot\sqrt{3}+\frac{1}{2}}$$

The ratio of the modulus of the maximum continuous velocity of the etheron to the modulus of the minimum continuous velocity of the etheron:

$$\frac{v_{æmax}}{v_{æmin}} = \frac{ τb_æ\cdot\sqrt{3}+1 }{τb_æ\cdot\sqrt{3}} = 1 + \frac{1}{ τb_æ\cdot\sqrt{3}} = 1+ v_{æmax} $$

The ratio of the modulus of the maximum continuous velocity of the etheron to the modulus of the average continuous velocity of the etheron:

$$\frac{v_{æmax}}{v_{æavg}} = \frac{ τb_æ\cdot\sqrt{3}+\frac{1}{2} }{τb_æ\cdot\sqrt{3} + 1}$$

The difference between the module of the maximum continuous speed of etheron and the module of the minimum continuous speed of etheron:

$$
\begin{aligned}
{v_{æmax}}-{v_{æmin}} = \frac{1}{ τb_æ\cdot\sqrt{3}} - \frac{1}{ τb_æ\cdot\sqrt{3}+1} = \frac{ τb_æ\cdot\sqrt{3}+1 - τb_æ\cdot\sqrt{3}}{(τb_æ\cdot\sqrt{3})\cdot (τb_æ\cdot\sqrt{3}+1)} = \\\\ = \frac{ 1}{(τb_æ\cdot\sqrt{3})^2+ (τb_æ\cdot\sqrt{3})}
\end{aligned}
$$

At the minimum value of the basic duration of the movement of etheron from cell to cell ($τb_æ=3$), the modules of continuous etheron velocities have a maximum range, approximately equal to the range from $0.9 \cdot v_{æavg}$ to $1.1 \cdot v_{æavg}$.

The inertness vector of the etheron $\vec{i}_æ$ is a vector directed opposite to the unit vector of the continuous velocity of the etheron $\hat{v}_{\text{æ}}$ and having a modulus equal to the ratio of the "total additional delay" of the etheron $a_æ$ to the reference distance $D_Æ$. In its meaning, the modulus of the inertness vector of the etheron is a "normalized delay".

$$i_æ=|\vec{i}_æ|=\frac{a_æ}{D_Æ}$$

$$i_{æavg}=\frac{a_{æavg}}{D_Æ}=\frac{1}{2}$$

$$a_æ=i_æ \cdot D_Æ$$

$$v_æ=\frac{D_Æ }{ τ_Æ + i_æ \cdot D_Æ }= \frac{1}{ τb_æ\cdot\sqrt{3} + i_æ }$$

$$i_æ=\frac{1}{v_æ}-τb_æ\cdot\sqrt{3}$$

$$\hat{i}_æ=-\hat{v}_æ = -\frac{\vec{d_æ}}{D_Æ}$$

$$\vec{i}_æ = \hat{i}_æ \cdot |\vec{i}_æ| = -\hat{v}_æ \cdot \frac{a_æ}{D_Æ}=-\frac{\vec{d_æ}}{D_Æ} \cdot \frac{a_æ}{D_Æ} = -\frac{\vec{d_æ}\cdot{a_æ}}{D_Æ^2}$$

$$\vec{d}_æ = -\frac{\vec{i}_æ \cdot D_Æ }{ |\vec{i}_æ|}$$

$$\vec{v_æ} = -\frac{\vec{i}_æ \cdot D_Æ }{ |\vec{i}_æ| \cdot (τ_Æ + |\vec{i}_æ| \cdot D_Æ)}= -\frac{\vec{i}_æ}{ |\vec{i}_æ| \cdot (τb_æ\cdot\sqrt{3} + |\vec{i}_æ|)}$$

The modulus of the inertness vector of the etheron $\lvert \vec{i}\_{\text{æ}} \rvert$ is equal to zero at the maximum continuous velocity of the etheron $v_{æmax}$ and is maximum at the minimum continuous velocity of the etheron $v_{æmin}$.

The unit of measurement for inertness in the ether system of units is "æi".

The interaction of several etherons in a space cell reduces to changing the second and third parameters of these etherons, as well as possibly changing the fourth and fifth parameters of these etherons.

During the interaction of several etherons in a space cell, the absolute position of this space cell is entered into the second parameter of each etheron.
During the interaction of several etherons in a space cell, the current time tick is entered into the third parameter of each etheron.

During the interaction of only two etherons in a space cell, the fourth parameter and fifth parameter of each of these etherons do not change.

Transit interaction of etherons is considered to be interaction of etherons, in which the speeds and directions of etherons do not change.

Interaction of only two etherons in a cell of space is always a "transit interaction" of etherons. Transit interactions can be not only two-etheron interactions.

The velocity of an etheron over the aggregate of free motions of the etheron alternating with only transit interactions of etherons is called "transit velocity".

The transit velocity of an etheron is always less than the continuous velocity of the etheron and depends on the probability of transit interaction with other etherons.

During the interaction of three or more etherons in a space cell, the fourth and fifth parameters of each of these etherons change in accordance with the "substance-field pattern" of the distribution of relative continuous velocities of etherons in the group of etherons, as well as in accordance with the law of conservation of momentum, in accordance with the law of conservation of energy, and in accordance with the range of absolute continuous velocities of etherons.

When three or more etherons interact in a cell of space, the fourth and fifth parameters of each of these etherons can change in accordance with the "substance-field pattern" of the distribution of continuous velocities of etherons in a group of etherons, as well as in accordance with the "law of conservation of inertness" and in accordance with the range of absolute continuous velocities of etherons. If there is no satisfactory solution to the problem of distributing continuous velocities for the parameters of the interacting etherons, then after the interaction, the velocities and directions of the interacting etherons remain unchanged, and the interaction itself is considered transit.

The "law of conservation of inertness" during the interaction of three or more etherons in a cell of space consists in the fact that for collision etherons in a cell of space, the "sum of their inertness vectors" ($\vec{I_c}$) before the collision is equal to the "sum of their inertness vectors" after the collision, and also the "sum of their inertness vector moduli" (${ℐ_c}$) before the collision is equal to the "sum of their inertness vector moduli" after the collision:

$$\vec{I_c} = \sum_{i=1}^{N} \vec{i}_\text{æi} = const$$

$${ℐ_c} = \sum_{i=1}^{N}{i}_\text{æi} = const$$

The "law of conservation of inertness" states that during any interaction of etherons, the following are simultaneously conserved: the total vector of etheron inertness; and the total scalar inertness of etherons. The "law of conservation of inertness" includes the "first law of conservation of inertness" and the "second law of conservation of inertness."

The first law of conservation of inertness is equivalent to the conservation of the weighted sum of etheron directions:

$$\sum_{k=1}^{N} a_k \vec d_k = \mathrm{const}$$

The second law of conservation of inertness is equivalent to the conservation of the total delay:

$$\sum_{k=1}^{N} a_k = \mathrm{const}$$

The "law of conservation of inertness" can be written in its most compact form as the conservation of a pair of invariants under any collisions of etherons:

$$
\left(
\sum_{k=1}^{N}\vec i_k,
\sum_{k=1}^{N}|\vec i_k|
\right)
= \mathrm{const}
$$

The "law of conservation of inertness" can be written in its equivalent, most compact form as the conservation of a pair of invariants under any collisions of etherons:

$$
\left(
\sum_{k=1}^{N} a_k\vec d_k,
\sum_{k=1}^{N} a_k
\right)
= \mathrm{const}
$$

In the simplest model, the "amount of inertness" in the Universe is constant. "Σiæ=const" is a conventional notation for the constancy of the Universe's inertness. $\vec{I}{_Æ}$ is the "sum of the inertness vectors" of all etherons. ${ℐ_Æ}$ is the "sum of the inertness vector modules" of all etherons. Formulas for the constancy of the Universe's inertness:

$$Σiæ=const$$

$$\vec{I}_\text{Æ} = \sum_{i=1}^{m_\text{Æ}} \vec{i}_\text{æi} = \vec{0}$$

$${ℐ}_\text{Æ} = \sum_{i=1}^{m_\text{Æ}}{i}_\text{æi} = \frac{m_\text{Æ}}{2} $$

The interaction of three or more etherons in a cell of space with a change in the speeds and directions of the interacting etherons is called "synthesizing interaction" of etherons.

In the general case, the substance-field pattern of distribution of continuous velocities of etherons in a group of etherons means that some etherons in a group move relative to the trajectory of other etherons in the same group with approximately the same moduli of continuous velocities, but in different directions.

Etherons in a group of etherons, moving relative to the trajectory of other etherons in the same group with approximately the same modules of continuous velocities, but in different directions, are called "field etherons".

Etherons in a group of etherons, relative to the trajectory of which other etherons in the same group move with approximately the same modules of continuous velocities, but in different directions, are called "substantial etherons".

In the simplest version of the substance-field pattern, for any "group of collision etherons" ($Æ_c$), their "delays" and "directions" after a collision are calculated in such a way that one etheron, whose "inertness vector modulus" ($\lvert \vec{i}\_{\text{æ}} \rvert$) is greater than the "inertness vector moduli" of the other etherons in the collision, becomes a substantial etheron ($æs$), while all other etherons in the collision become field etherons ($æf$). After which, the same "inertness vector modulus" ($\lvert \vec{i}\_{\text{æf}} \rvert$) is first calculated for all field etherons, provided that the directions of the field etherons do not change after the collision, that the "inertness vector moduli" do not go beyond the range of the "inertness vector moduli", and that the law of conservation of inertness is satisfied. The "inertness vector" of the substantial etheron ($\vec{i}$<sub>æs</sub>) is then calculated, from which the "delay" ($a_{æs}$) and "direction" ($\vec{d}$<sub>æs</sub>) of the substantial etheron are obtained. The new "delay" and "direction" for the substantial etheron will compensate for changes in the "inertness vector magnitudes" of the field etherons.

The first version of the algorithm for selecting a substantial etheron in the "group of collision etherons in a cell of space" ($Æ_c$) comes down to finding the "etheron index" ($æ_s$) with the maximum value of the inertness vector modulus ($\lvert \vec{i}\_{\text{æ}} \rvert$), which is equivalent to finding the "etheron index" ($æ_s$) with the maximum value of the "delay" parameter ($a_æ$):

$$æ_s = \arg\max_{æ \in Æ_c} (|\vec{i}_\text{æ}|)$$

$$æ_s = \arg\max_{æ \in Æ_c} (a_\text{æ})$$

The second variant of the algorithm for selecting a substantial etheron in the "group of collision etherons in a cell of space" ($Æ_c$) comes down to finding the "etheron index" ($æ_s$) with the minimum value of the modulus of the difference between the modulus of the inertness vector ($\lvert \vec{i}\_{\text{æ}} \rvert$) and the "average value from the range for the moduli of the inertness vectors" ($\frac{1}{2}$), which is equivalent to finding the "etheron index" ($æ_s$) with the value of the "delay" parameter ($a_æ$) closest to $\frac{D_Æ}{2}$:

$$æ_s = \arg\min_{æ \in Æ_c} (||\vec{i}_\text{æ}| - \frac{1}{2}|)$$

$$æ_s = \arg\min_{æ \in Æ_c} (|a_æ - \frac{D_\text{Æ}}{2}|)$$

The third version of the algorithm for selecting a substantial etheron in a "group of collision etherons in a cell of space" ($Æ_c$) takes into account the vectors of the etheron directions and comes down to finding the "etheron index" ($æ_s$) with the minimum value of the modulus of the difference between the "inertness vector of a collision etheron" ($\vec{i}$<sub>æ</sub>) and the "sum of the inertness vectors of all collision etherons in a cell":

$$æ_s = \arg\min_{æ \in Æ_c} (| \vec{i}_\text{æ} - \sum_{æ \in Æ_c} \vec{i}_\text{æ} |)$$

The algorithm for calculating the simplest version of the substance-field pattern for a group of collision etherons in the amount equal to $N$, in the analytical version is reduced to solving the quadratic equation $ax²+bx+c=0$, where $x=i_{æf}$ is the modulus of the inertness vector of each field etheron after the collision. The formulas of the algorithm contain the following notations. Vectors are denoted by symbols with an arrow on top. Unit vectors are denoted by symbols with a cap on top. Vector moduli are denoted either by simple symbols or by symbols with an arrow on top in two vertical lines around the symbols. The number of a substantial etheron is equal to $N$. Field etheron numbers start with $1$ and end with $N-1$. $\vec{i}$<sub>æs</sub> is the inertness vector of a substantial etheron after the collision. $\vec{i}$<sub>æj</sub> is the inertness vector of an etheron with the number $j$ before the collision. $\vec{I}$<sub>old</sub> is the sum of the inertness vectors of all etherons before the collision. $\vec{I}$<sub>new</sub> is the sum of the inertness vectors of all etherons after the collision. $ℐ_{\text{old}}$ is the sum of the moduli of the inertness vectors of all etherons before the collision. $ℐ_{\text{new}}$ is the sum of the moduli of the inertness vectors of all etherons after the collision. Formulas for the calculation algorithm of the simplest version of the substance-field pattern:

$$\vec{I}_{\text{old}} = \sum_{j=1}^N \vec{i}_{æj}$$

$$\vec{I}_{\text{new}} = \sum_{j=1}^{N-1} i_{æf} \cdot \hat{i}_{æj} + \vec{i}_{æs}$$

$$\vec{I}_{\text{new}} = \vec{I}_{\text{old}}$$

$$ℐ_{\text{old}} = \sum_{j=1}^N {i}_{æj}$$

$$ℐ_{\text{new}} = (N-1)\cdot i_{æf} + i_{æs}$$

$$ℐ_{\text{new}} = ℐ_{\text{old}}$$

$$\vec{i}_{æs} = \sum_{j=1}^N \vec{i}_{æj} - i_{æf}\cdot \sum_{j=1}^{N-1} \hat{i}_{æj}$$

$$(N-1) \cdot i_{æf} +  |\sum_{j=1}^N \vec{i}_{æj} - i_{æf} \sum_{j=1}^{N-1} \hat{i}_{æj}| = \sum_{j=1}^N {i}_{æj}$$

$$|\sum_{j=1}^N \vec{i}_{æj} - i_{æf} \cdot\sum_{j=1}^{N-1} \hat{i}_{æj}|^2 = (\sum_{j=1}^N {i}_{æj} - (N-1) \cdot i_{æf})^2 $$

$$
\begin{aligned}
|\sum_{j=1}^N \vec{i}_{æj}|^2 + i_{æf} ^2 \cdot| \sum_{j=1}^{N-1} \hat{i}_{æj}|^2 - 2\cdot i_{æf} \cdot(\sum_{j=1}^N \vec{i}_{æj})\cdot (\sum_{j=1}^{N-1} \hat{i}_{æj}) = \\\\ = (\sum_{j=1}^N {i}_{æj})^2 + ((N-1) \cdot i_{æf})^2 - 2\cdot (\sum_{j=1}^N {i}_{æj}) \cdot ((N-1) \cdot i_{æf})
\end{aligned}
$$

$$
\begin{aligned}
i_{æf} ^2 \cdot (| \sum_{j=1}^{N-1} \hat{i}_{æj}|^2-(N-1)^2) + \\\\ + i_{æf}  \cdot (-2\cdot(\sum_{j=1}^N \vec{i}_{æj})\cdot (\sum_{j=1}^{N-1} \hat{i}_{æj}) + 2\cdot (\sum_{j=1}^N {i}_{æj}) \cdot (N-1 )) + \\\\ + (|\sum_{j=1}^N \vec{i}_{æj}|^2-(\sum_{j=1}^N {i}_{æj})^2)=0
\end{aligned}
$$

$$a \cdot i_{æf}^2 + b \cdot i_{æf} + c = 0$$

$$i_{æf} = \frac{-b \pm \sqrt{b^2 - 4\cdot a \cdot c}}{2\cdot a}$$

$$a_{æf} = i_{æf} \cdot D_Æ$$

$$a_{æs} = |\vec{i}_{æs}| \cdot D_Æ$$

$$\vec{d}_{æs} = -\frac{\vec{i}_{æs} \cdot D_Æ }{ |\vec{i}_{æs}|}$$

In the iterative version, the algorithm for calculating the simplest version of the substance-field pattern for a group of collision etherons in a quantity equal to $N$ can be based on the Newton-Raphson method for solving the conservation equation. Maximum number of iterations: $K_{\max}$. Accuracy: $\varepsilon = 10^{-8}$. If $\lvert \vec{V}^{(k)} \rvert = 0$, then use the bisection method. If $i_{æf}^{(k)} \notin [0, 1]$, then project onto the permissible range.

$$i_{æf}^{(0)} = \frac{ℐ_{\text{old}}}{N}, \quad k = 0$$

$$\vec{U} = \sum_{j=1}^{N-1} \hat{\vec{i}}_\text{æj}$$

$$NEXT: \vec{V}^{(k)} = \vec{I}_\text{old} - i_{æf}^{(k)} \cdot \vec{U}$$

$$F(i_{æf}^{(k)}) = (N-1) \cdot i_{æf}^{(k)} + |\vec{V}^{(k)}| - ℐ_{\text{old}}$$

$$F'(i_{æf}^{(k)}) = (N-1) - \frac{\vec{V}^{(k)} \cdot \vec{U}}{|\vec{V}^{(k)}|}$$

$$i_{æf}^{(k+1)} = i_{æf}^{(k)} - \frac{F(i_{æf}^{(k)})}{F'(i_{æf}^{(k)})}$$

$$\text{IF } (|i_{æf}^{(k+1)} - i_{æf}^{(k)}| < \varepsilon) \text{ THEN } i_{æf} = i_{æf}^{(k+1)}$$

$$\text{ELSE } \{ k = k + 1; \text{GOTO NEXT} \}$$

The interaction of etherons in a cell of space, as a result of which the modules of continuous velocities and reference directions of etherons have changed, is called synthesizing due to the synthesis from this group of etherons of an etheric object of the second level of matter, consisting of substantial and field etherons.

An ether object of the second level of matter is conventionally called "ether batch".

An etheron that has become a field etheron during synthesizing interaction is called "scattered field etheron".

An etheron that has become a substantial etheron during synthesizing interaction with a scattered field etheron and another etheron is called "dragged field etheron".

An etheron that has become a substantial etheron during synthesizing interaction with a dragged field etheron and another etheron is also called "dragged field etheron".

Ether is called multirole due to the fact that etherons perform different inertial roles.

Substantial etherons of an ether hyperobject form the "ether substance" of the ether hyperobject.

The spatial, temporal, and velocity parameters of the ether substance of an ether hyperobject constitute the configuration of the ether substance of the ether hyperobject.

Field etherons of an ether hyperobject form the "ether field" of the ether hyperobject.

Usually, an ether hyperobject has ether substance and ether field.

Field etherons of an ether hyperobject can be low-speed and high-speed.

The spatial, temporal, and velocity parameters of the ether field of an ether hyperobject constitute the configuration of the ether field of the ether hyperobject.

The configuration of the ether field of an ether hyperobject depends on the configuration of the ether substance of the ether hyperobject and on the configuration of the external ether.

The configuration of the ether substance of an ether hyperobject and the configuration of the ether field of an ether hyperobject constitute the configuration of the ether hyperobject.

Ether fields of ether hyperobjects obey the "principle of ether superposition".

The principle of ether superposition means that the ether fields of ether subhyperobjects of an ether hyperobject overlap each other and form the ether field of the ether hyperobject.

Etherons of the ether substance of an ether batch are located in space cells positioned close to each other. The directions of absolute continuous motion and absolute continuous velocities of etherons of the ether substance of an ether batch are approximately the same.

The ether field of an ether batch is called "batch ether field".

The batch ether field always lags behind the ether substance of the ether batch.

The frequency parameters of the batch ether field of an ether batch are determined by the substance-field pattern of the distribution of relative continuous velocities of etherons in the group of etherons after each synthesizing interaction of any etheron of the ether batch with external etherons. Each synthesizing interaction of any etheron of the ether batch with external etherons leads to the scattering of field etherons with approximately the same moduli of relative continuous velocities, but in different directions. The moduli of relative continuous velocities of scattered field etherons from different synthesizing interactions of etherons of the ether batch with external etherons usually differ.

Ether batches can pass through each other.

The average absolute continuous velocity of an ether batch is approximately equal to C.

During the synthesizing interaction of etherons, the ether substance of the synthesized ether batch accelerates in the direction of the difference between the vector sum of the continuous velocity vectors of the substantial etherons after the interaction and the vector sum of the continuous velocity vectors of these etherons before the interaction.

Acceleration of an etheron of the first ether hyperobject in the direction toward the etherons of the ether substance of the second ether hyperobject during synthesizing interaction of this etheron with an etheron of the ether field of the second ether hyperobject and with an external etheron is called attraction of the etheron of the first ether hyperobject to the second ether hyperobject.

Most often, attraction of an etheron of the first ether hyperobject to the second ether hyperobject occurs during synthesizing interaction of this etheron with a low-speed etheron of the ether field of the second ether hyperobject and with a high-speed medium etheron. In this case, it is considered that attraction by the ether field of the second ether hyperobject of the etheron of the first ether hyperobject to the second ether hyperobject occurs, and that repulsion by the ether medium of the etheron of the first ether hyperobject in the direction toward the second ether hyperobject occurs. At the same time, the modulus of the absolute continuous velocity of the high-speed etheron of the ether medium decreases. As a result of such decreases in the moduli of absolute continuous velocities of high-speed etherons of the ether medium, the repulsive ability of the ether medium decreases with decreasing distance to the ether substance of the second ether hyperobject, and the attractive ability of the ether medium increases with decreasing distance to the ether substance of the second ether hyperobject.

Attraction of the first ether hyperobject in the direction toward the second ether hyperobject consists of attractions of etherons of the first ether hyperobject to the second ether hyperobject.

Acceleration of an etheron of the first ether hyperobject in the direction away from the etherons of the ether substance of the second ether hyperobject during synthesizing interaction of this etheron with an etheron of the ether field of the second ether hyperobject and with an external etheron is called repulsion of the etheron of the first ether hyperobject from the second ether hyperobject.

Most often, repulsion of an etheron of the first ether hyperobject from the second ether hyperobject occurs during synthesizing interaction of this etheron with a high-speed etheron of the ether field of the second ether hyperobject and with a low-speed medium etheron. In this case, it is considered that repulsion by the ether field of the second ether hyperobject of the etheron of the first ether hyperobject from the second ether hyperobject occurs, and that attraction by the ether medium of the etheron of the first ether hyperobject in the direction away from the second ether hyperobject occurs. At the same time, the modulus of the absolute continuous velocity of the high-speed etheron of the ether field of the second ether hyperobject decreases. As a result of such decreases in the moduli of absolute continuous velocities of high-speed etherons of the ether field of the second ether hyperobject, the repulsive ability of the ether field of the second ether hyperobject decreases with increasing distance to the ether substance of the second ether hyperobject, and the attractive ability of the ether field of the second ether hyperobject increases with increasing distance to the ether substance of the second ether hyperobject.

Repulsion of the first ether hyperobject in the direction away from the second ether hyperobject consists of repulsions of etherons of the first ether hyperobject from the second ether hyperobject.

Together, attraction and repulsion constitute "ether field interaction" of ether hyperobjects.

The result of ether field interaction of two ether hyperobjects can be either acceleration toward each other or acceleration away from each other.

Synchronization of the motion of one ether hyperobject with changes in the ether fields of other ether hyperobjects can lead to predominance of attraction to other ether hyperobjects or predominance of repulsion from other ether hyperobjects. Predominance of attraction to other ether hyperobjects or predominance of repulsion from other ether hyperobjects as a result of synchronization of the motion of one ether hyperobject with changes in the ether fields of other ether hyperobjects is called "ether field synchronization".

Due to synthesizing interactions of etherons of an ether batch with external etherons, the mass of the ether batch can grow to a certain value, and the ether batch can increase its degree of stability.

The speed of an etheron over the aggregate of free motions of the etheron alternating with transit interactions of etherons and synthesizing interactions of etherons is called "effective speed".

The speed of light in vacuum is close to the average absolute effective speed of an etheron.

An ether object of the third level of matter is called "ether spiral".

An ether spiral is a spiral cluster of ether batches united by ether fields of ether batches. In an ether spiral, there is a "leading ether batch" and one or more "follower ether batches," which are held by the ether field of the leading ether batch. The follower ether batches of the ether spiral orbitally rotate around the trajectory of motion of the leading ether batch of the ether spiral.

The ether field of an ether spiral is called "spiral ether field".

The frequency parameters of the spiral ether field of an ether spiral are determined by the periodicity of motion of the follower ether batches in the ether spiral. The greater the mass of a follower ether batch in the ether spiral, the lower the speed of orbital rotation of this ether batch around the trajectory of motion of the leading ether batch of the ether spiral. The frequency parameters of ether spirals have natural limitations, as the mass of an ether spiral has natural limitations.

Ether spirals can pass through each other.

The average absolute continuous velocity of an ether spiral is approximately equal to C.

The configuration of an ether spiral determines its ether field interaction with other ether spirals.

If the frequency of the first ether spiral is higher than the frequency of the second ether spiral, then the first ether spiral is "negative" relative to the second ether spiral, and the second ether spiral is accordingly "positive" relative to the first ether spiral, and these ether spirals attract.

If the frequency of the first ether spiral is approximately equal to the frequency of the second ether spiral, then the first ether spiral is "neutral" relative to the second ether spiral, and these ether spirals repel.

One and the same ether spiral of a certain frequency can simultaneously be "positive" relative to an ether spiral with a higher frequency, "neutral" relative to an ether spiral with a similar frequency, "negative" relative to an ether spiral with a lower frequency.

The laws of ether spirals determine multi-level layered clustering of ether spirals in elementary atoms.

The laws of ether spirals also determine multi-level hierarchical clustering of elementary atoms in nonelementary atoms.

Light is radiation consisting of sparse packets of ether spirals. The ether spirals of a light packet are practically not connected to each other. The packet of ether spirals of light is formatted by the periodic motion of the radiation source. The packet of ether spirals in some non-ether physical interpretations is called a "photon". The wavelength of the light packet of ether spirals is determined by the frequency parameters of the motion of the radiation source.

An ether object of the fourth level of matter is called "ether major".

An ether major is a chaotic cluster of ether spirals united by ether fields of ether spirals. Ether majors include protium atoms, protons, neutrons, extra-atomic electrons, positrons, as well as some other particles.

The ether field of an ether major is called "major ether field".

An ether major has spin.

The average absolute effective velocity of an ether major can be zero.

The major ether field can be omnidirectional.

The frequency parameters of the major ether field are determined by the periodicity of motion of ether spirals in the ether major, as well as the mass of the ether major and the configuration of the ether major.

The major ether field can be conditionally divided into two components - into "electric field" and "magnetic field". The electric field is the superimposed spiral ether fields of ether spirals moving in different directions. The magnetic field is the superimposed spiral ether fields of ether spirals moving in the same direction.

The electric charge of an ether hyperobject is determined by the predominance in the ether hyperobject of ether spirals with frequency parameters in a certain range.

Electric charge in ether theory is not two-signed, but multi-signed. The sign of electric charge depends on the configuration of the ether spirals predominant in the ether hyperobject. The lower the range of frequency parameters of the ether spirals predominant in the ether hyperobject, the higher the sign of the electric charge of the ether hyperobject. The number of signs of electric charge is limited, as the frequency parameters of ether spirals have natural limitations.

The first electric charge is "negative" electric charge. The sign of the first electric charge is the sign "-". Instead of the sign "-" for the first electric charge, the sign "1" can be used. The second electric charge is "positive" electric charge. The sign of the second electric charge is the sign "+". Instead of the sign "+" for the second electric charge, the sign "2" can be used. The sign of the third electric charge is "3", fourth - "4", fifth - "5", sixth - "6", seventh - "7", eighth - "8", ninth - "9", tenth - "A", eleventh - "B", twelfth - "C", thirteenth - "D", fourteenth - "E", fifteenth - "F", and so on up to some limiting sign.

Ether hyperobjects with electric charge of the same sign electrically repel. Ether hyperobjects with electric charges of different signs electrically attract. The closer the signs of electric charges are to each other, the greater the force of electric attraction of ether hyperobjects with electric charges of these signs. The higher the signs of electric charges, the greater the force of electric attraction and electric repulsion of ether hyperobjects with electric charges of these signs.

The flow of ether spirals in a cluster of ether spirals is "electric current". Packets of ether spirals of light are not electric current.

Oppositely directed flows of ether spirals with approximately the same parameters of ether spirals repel. Unidirectional flows of ether spirals with approximately the same parameters of ether spirals attract.

Proteon is the general name for the protium atom, proton, and neutron. The term "proteon" in hyperatomic physics is an alternative to the term "nucleon" in nuclear physics.

The simplest notation for the Protium atom is H. The symbol for the Protium atom, with its atomic mass, is H-1. The symbol for the Protium atom without the H sign and with the atomic mass indicated is 1.

A proteon is considered an "elementary atom".

The protium atom has several layers with increased probability of finding ether spirals with mass in a certain range in them. The deeper, the more often heavier ether spirals can be found in the proteon. The closer to the surface, the more often lighter ether spirals can be found in the proteon. In the outer layer of the protium atom, the probability of finding ether spirals of the smallest mass is maximum. The upper layers of the protium atom are called the "atmosphere of the atom" of protium. The lower layers of the protium atom are called the "clot of the atom" of protium. In nuclear-electronic atomic models, the outer layer of the protium atom is considered the "atomic electron".

Usually, an "extra-atomic electron" arises as a result of clustering of light ether spirals ejected from the outer layer of the atmosphere of the protium atom.

A proton is a protium atom that has lost its outer layer.

Proteons are usually synthesized in the inner cores of planets and in the inner cores of stars from ether spirals captured by the gravity of these cosmic bodies. Superheavy proteons in the inner cores of planets and in the inner cores of stars can divide into proteons of smaller masses.

The "Ether Proteon Model" is the first part of the "Ether Atomic Model". In the English version, the abbreviation for "Ether Atomic Model" is "ÆAM". In the English version, the abbreviation for "Ether Proteon Model" is "ÆPM".

An ether object of the fifth level of matter is called "hyperatom".

A hyperatom is a hierarchical cluster of proteons united by proteon ether fields and strong common multilayered atmospheres consisting of ether spirals.

A hyperatom is considered a "non-elementary atom".

The hierarchy of a cluster of ether objects of any type means that a complex cluster of ether objects of this type consists of less complex clusters of ether objects of this type, and that less complex clusters of ether objects of this type in turn consist of even less complex clusters of ether objects of this type, and so on up to the ether objects of this type themselves.

The hierarchy of a hyperatom means that a complex hyperatom consists of less complex hyperatoms, and that less complex hyperatoms in turn consist of even less complex hyperatoms, and so on up to the proteons themselves.

The Protium atoms in a hyperatom are called Protium subatoms. A Protium subatom is an elementary subatom.

Hyperatoms can be sub-objects of higher-level hyperatoms. Hyperatoms in higher-level hyperatoms are called subhyperatoms. A subhyperatom is a non-elementary subatom. Subhyperatoms in a hyperatom also have a strong common multi-layered atmosphere consisting of ether spirals.

If the statement refers to an "atom" and not to a "Protium atom", then it refers to an atom as such, which could be a Protium atom or any hyperatom. If the statement refers to "atoms", then it refers to atoms as such, which could be Protium atoms or any hyperatoms.

If the statement refers to a "subatom" and not to a "Protium subatom", then it refers to a subatom as such, which could be a Protium subatom or any subhyperatom. If the statement speaks of "subatoms", then it is about subatoms as such, which can be both Protium subatoms and any subhyperatoms.

In stable hyperatoms there are no protons and neutrons, but only elementary subatoms and non-elementary subatoms.

The hyperatom's atmosphere of ether spirals of certain masses unites the hyperatom's subatoms and separates this hyperatom from other atoms.

Usually, the deeper the protium subatom in the hyperatom, the heavier and denser the ether spirals of this protium subatom.

Usually, a positron arises as a result of clustering of relatively heavy ether spirals ejected from the inner layer of the atmosphere of the protium atom.

Usually, a neutrino arises as a result of clustering of a small number of relatively light ether spirals that for one reason or another detached from the atmosphere of a hyperatom subatom.

The following paragraph provides several examples of the structure of simple hyperatoms. The combined cluster of two Protium subatoms with a strong common atmosphere forms the Deuterium hyperatom. The combined cluster of three Protium subatoms with a strong common atmosphere forms the Helithreeum hyperatom. Helithreeum is the name of the He-3 hyperatom in the ether hyperatomic model. Ht is the symbol for the chemical element Helithreeum and the symbol for the Helithreeum hyperatom. The combined cluster of the Deuterium subhyperatom and the Protium subatom with a strong common atmosphere forms the Tritium hyperatom. The combined cluster of two Deuterium subhyperatoms with a strong common atmosphere forms the Helium hyperatom. The combined cluster of the Helium subhyperatom and the Protium subatom with a strong common atmosphere forms the Helium-5 hyperatom.

Two Protium subatoms in a Deuterium hyperatom or two subatoms in a Deuterium subhyperatom are called "paired" Protium subatoms. If a Protium subatom in a hyperatom is not a subatom of a Deuterium hyperatom or a subatom of a Deuterium subhyperatom, then such a Protium subatom is called an "unpaired" Protium subatom.

A hyperatom configuration is a description of the hyperatom structure. A chemical element is a set of hyperatom configurations. A chemical subelement is a subset of a chemical element. The designation of a chemical subelement consists of the designation of the chemical element, the # sign, and the conventional ordinal number of the subelement. For example, He#1 is the designation of the first chemical subelement of the chemical element Helium, and He#2 is the designation of the second chemical subelement of the chemical element Helium.

Atomahedron is a general name for geometric shapes of hyperatoms and molecules. The basic atomahedrons are diatomahedron, triatomahedron, tetraatomahedron, pentaatomahedron. A diatomahedron is an atomahedron consisting of two atoms. A triatomahedron is a triangular atomahedron consisting of three atoms. A tetraatomahedron is an atomahedron-tetrahedron consisting of four atoms. A pentaatomahedron is an atomahedron in the form of a trigonal bipyramid consisting of five atoms. Hyperatomahedron is a general name for atomahedrons of the second and subsequent levels. Subatomahedron is a general name for atomahedrons in a hyperatomahedron. Subhyperatomahedron is a hyperatomahedron of the previous level in a hyperatomahedron of the next level. For example, the Deuterium hyperatom has the shape of a diatomahedron; The Helium hyperatom He-4 has the shape of a tetraatomahedron; the Zinc hyperatom Zn-64 has the shape of a third-level tetraatomahedron.

The tetrahedron is considered a periodic geometric shape of hyperatoms. The tetraatomahedron is considered a completed atomahedron. The pentaatomahedron is considered an overfilled atomahedron. Subhyperatoms of a hyperatomahedron may have an unfinished atomahedron of the previous level. The sequence of configurations of hyperatoms in the sequential hierarchical filling of a periodic hyperatomic geometric shape with Protium subatoms is considered "primary" and forms a "primary sequence of hyperatoms". The hierarchical filling of a periodic hyperatomic geometric shape means that a Protium subatom, when added to an unpaired Protium subatom, forms a Deuterium hyperatom or a Deuterium subhyperatom with it, and also means that subhyperatoms also form pairs. Hyperatoms of the primary sequence of hyperatoms are called primary. The atomic mass of a primary hyperatom can be used as a full designation for this hyperatom. For example, 1 is the designation for a Protium atom; 2 is the symbol for the hyperatom of Deuterium; 3 is the symbol for the hyperatom of Tritium; 4 is the symbol for the hyperatom of Helium; 5 is the symbol for the hyperatom of Helium-5.

A hyperatom is usually notated so that the structure of the hyperatom can be uniquely identified. A hyperatom notation may include the notation of the chemical element of the hyperatom, the atomic mass of the hyperatom, and the formula of the hyperatom. The parts of a hyperatom notation are separated from each other by the - sign. For example, D is the simplest symbol for the hyperatom of Deuterium. D-2 is the symbol for the hyperatom of Deuterium with its atomic mass indicated. 2 is the symbol for the hyperatom of Deuterium with only its atomic mass indicated, which is the primary atomic mass. A hyperatom can be designated by indicating only its atomic mass only if the hyperatom is part of the primary sequence of hyperatoms.

The formula of a hyperatom is an expression consisting of the designations of the subatoms of that hyperatom, separated by an apostrophe ' and joined by parentheses. For example, (H'H) is the formula of the hyperatom of Deuterium D-2. The formula of a hyperatom can be specified in the designation of the hyperatom. The formula of a hyperatom in the designation of a hyperatom is separated by the - sign. For example, D-2-(H'H) is the designation of the hyperatom of Deuterium D-2, which contains the formula of the hyperatom of Deuterium D-2.

The following paragraph provides several examples of notations for simple hyperatoms. H-1-1. D-2-(1'1). T-3-(2'1). Ht-3-(1'1'1). He-4-(2'2). He-5-(4'1). Li-6-(4'2). Li-7-(4'3). Be-8-(4'4). Be-9-(8'1). Be-10-(5'5). B-10-(8'2). B-11-(8'3). C-12-(8'4). C-13-(8'5). C-13-(12'1). N-14-(8'6). N-15-(8'7). O-16-(8'8). O-17-(16'1). O-18-(16'2). F-19-(16'3). Ne-20-(16'4). Ne-21-(16'5).

Usually, a hyperatom consists of two subatoms. In three subatoms of a hyperatom, a skew in the distribution of the binding spiral mass of the hyperatom usually arises toward one of the pairs of subatoms of the hyperatom, as a result of which this pair of subatoms of the hyperatom either forms a subhyperatom in this hyperatom or pushes out the third subatom from the hyperatom, transforming the original hyperatom with three subatoms into a molecule consisting of a hyperatom now with two subatoms and the former third subatom that has become a separate atom.

A neutron is a protium subatom that for one reason or another left its hyperatom and lost part of its outer layer. The parameters of a neutron mainly depend on where in the hyperatom the protium subatom that became this neutron was located.

A neutron upon entering a hyperatom can capture part of the hyperatom's atmosphere with its ether field. The loss by the hyperatom of part of its atmosphere upon entry of a neutron reduces the stability of the hyperatom.

A proton upon entering a hyperatom can capture part of the hyperatom's atmosphere with its ether field. The loss by the hyperatom of part of its atmosphere upon entry of a proton reduces the stability of the hyperatom.

A light hyperatom upon entering a heavy hyperatom can capture part of the heavy hyperatom's atmosphere with its ether field. The loss by the heavy hyperatom of part of its atmosphere upon entry of a light hyperatom reduces the stability of the heavy hyperatom.

Hyperatoms are synthesized in the inner cores of planets and in the inner cores of stars. The synthesis of hyperatoms occurs with accumulation of energy, not with release of energy. Outside the cores of planets and outside the cores of stars, heavy hyperatoms begin to decay with release of energy.

A hyperatom can lose part of its ether spirals as a result of external influence. The loss of ether spirals by a hyperatom reduces the stability of the hyperatom. A decrease in the stability of a hyperatom can lead to the decay of the hyperatom into subatoms.

The decay of hyperatoms into subatoms is accompanied by expansion of these subatoms. The expanding subatoms of the decaying hyperatom collide. The collision of expanding subatoms of the decaying hyperatom leads to the scattering of subatoms with certain velocities. Usually, in the decay of a hyperatom into subatoms, most of the energy is provided by the scattering subatoms released from the hyperatom, not by the ether spirals released from the hyperatom.

The "Ether Hyperatomic Model" is the second part of the "Ether Atomic Model". In the English version, the abbreviation for "Ether Hyperatomic Model" is "ÆHAM".

The Ether Atomic Model is a model of elementary atoms and a model of nonelementary atoms.

The stability of a hyperatom upon entry of a neutron depends on the place in the hyperatom where this neutron entered. The entry of a neutron into a hyperatom can lead to the decay of the hyperatom.

A reactor designed for controlled decay of hyperatoms by protons and neutrons is called a "hyperatomic reactor". For simplicity, a hyperatomic reactor can be conventionally called an "ether reactor".

In a hyperatomic reactor, hyperatoms and proteons in targets and beams must be oriented so that upon collision of hyperatoms with proteons and hyperatoms with hyperatoms, the highest probability of the necessary hyperatomic reactions is ensured. In a hyperatomic reactor, hyperatoms and proteons are specially oriented by an external magnetic field.

So-called "thermonuclear reactors" are considered in the ether atomic model as "hyperatom decay reactors," not "hyperatom synthesis reactors".

An ether object of the sixth level of matter is called a "molecule".

A molecule is a cluster of atoms united by their ether fields and having a weak common atmosphere of ether spirals. Molecules include the hydrogen molecule, oxygen molecule, water molecule, and all other molecules.

The "Ether Molecular Model" is a physical model of molecules based on the ether atomic model. In the English version, the abbreviation for "Ether Molecular Model" is "ÆMM".

Molecules can be conditionally divided into hierarchical levels. A simple molecule can be a subobject of a complex molecule. A subobject of a complex molecule is called a "submolecule". A complex molecule is called a "hypermolecule". A complex submolecule is called a "subhypermolecule".

The formula of a molecule is an expression consisting of the designations of the atoms of that molecule, separated by the caret sign ^ and united by parentheses. For example, (H^H) is the formula of the Hydrogen molecule H₂. The formula of a molecule can be indicated in the designation of the molecule. The formula of a molecule in the designation of a molecule is separated by the - sign. For example, H₂-(H^H) is the designation of the Hydrogen molecule H₂, which contains the formula of the Hydrogen molecule H₂.

The disintegration of heavy hyperatoms outside the planet's core in the early stages of the planet's existence after the planet's surface has cooled results in the energy-provided diversity of organic molecular forms, objects and processes necessary for the emergence of primary living ether objects. The disintegration into identical subatoms of identical heavy hyperatoms in a single chain of submolecules in a hypermolecule can lead to the transformation of this hypermolecule into a double-chain one. The copper hyperatom Cu-62-(31'31) consists of two phosphorus subhyperatoms P-31-(16'15). The copper hyperatom Cu-62-(31'31) is an unstable hyperatom. The copper hyperatom Cu-62-(31'31) usually disintegrates into two phosphorus hyperatoms P-31-(16'15). ProtoDNA is a hypermolecule that is a single chain of subhypermolecules of double protonucleotides. The subhypermolecule of the double protonucleotide is a subhypermolecule consisting of a copper hyperatom Cu-62-(31'31) linked by submolecular bonds to the base of the double protonucleotide. The base of the double protonucleotide is that part of the subhypermolecule of the double protonucleotide that does not include the copper hyperatom Cu-62-(31'31) itself. The base of the double protonucleotide corresponds to two complementary nucleotides without phosphorus hyperatoms P-31-(16'15). When one copper hyperatom Cu-62-(31'31) in the protoDNA hypermolecule disintegrates into two phosphorus hyperatoms P-31-(16'15), the subhypermolecule of the double protonucleotide is transformed into an ordinary double complementary nucleotide, which is an element of the double chain in an ordinary DNA hypermolecule. When all copper hyperatoms Cu-62-(31'31) in a protoDNA hypermolecule disintegrate, the protoDNA hypermolecule becomes a regular DNA hypermolecule. Sometimes, when the last copper hyperatom Cu-62-(31'31) in a protoDNA hypermolecule disintegrates, the two nucleotide chains of the resulting regular DNA hypermolecule separate and become two complementary regular RNA hypermolecules. The transformation of a protoDNA hypermolecule into a DNA hypermolecule and the separation of a DNA hypermolecule into complementary RNA hypermolecules may, in some cases and under certain conditions, serve as the starting point of organic evolution. The explanation of the origin of life based on the transformation of protoDNA into DNA underlies the concept of "Ether Transformational Abiogenesis". The concept of "Etheric Transformational Abiogenesis" is a component of the "Ether Theory of Life".

An ether object of the seventh level of matter is called a "body".

A body is a cluster of atoms and molecules united by their ether fields. Bodies and parts of bodies can be in solid, liquid, and gaseous states. Bodies include primary galactic stars, stars, planets, asteroids, as well as all other clusters of atoms and molecules.

Bodies can be conditionally divided into hierarchical levels. A simple body can be a subobject of a complex body. A subobject of a complex body is called a "subbody". A complex body is called a "hyperbody". A complex subbody is called a "subhyperbody".

The "Ether Body Model" is a physical model of bodies based on the ether atomic model and ether molecular model. In the English version, the abbreviation for "Ether Body Model" is "ÆBM".

The "Ether Cosmic Body Model" is a physical model of cosmic bodies based on the ether body model. In the English version, the abbreviation for "Ether Cosmic Body Model" is "ÆCBM".

The "Ether Solar Model" is a physical model of the Sun based on the ether cosmic body model. In the English version, the abbreviation for "Ether Solar Model" is "ÆSM".

The cores of long-formed planets and the cores of long-formed stars are in a solid and cold state.

Planets and stars accumulate fissionable material in the form of accumulations of heavy hyperatoms. Accumulation of fissionable material above the critical mass in a cosmic body of near-stellar mass leads to a chain hyperatomic reaction of decay of heavy hyperatoms of the fissionable material. If the rate of accumulation of fissionable material in a cosmic body is higher than the rate of consumption of fissionable material in hyperatomic explosions of the fissionable material, then the cosmic body becomes an active star. The stability of heavy hyperatoms in an active star that has accumulated a certain mass can increase. An active star can go out due to an increase in the stability of heavy hyperatoms due to the growth of the star's mass. An extinct star, having accumulated fissionable material from heavier and unstable hyperatoms, can ignite again. Hyperatomic explosions of fissionable material in cosmic bodies of stellar mass can lead to the ejection of a large amount of the star's material into space. From the material ejected by cosmic bodies of stellar mass, cosmic bodies of planetary mass can form.

A "galactic prime" is the primary supermassive star of a galaxy.

A galactic prime, transitioning to an active state, can, as a result of hyperatomic explosions of its fissionable material, eject an amount of material sufficient for the formation of a star.

An ether object of the eighth level of matter is called an "astr".

An astr is a hierarchical cluster of cosmic bodies united by their etheric fields and moving along gravitational orbital trajectories. Astrs include planetary systems, star systems, galaxies, galaxy clusters, and larger-scale clusters.

Astrs can be conditionally divided into hierarchical levels. A simple astr can be a subobject of a complex astr. A subobject of a complex astr is called a "subastr". A complex astr is called a "hyperastr". A complex subastr is called a "subhyperastr".

The formula of an astr is an expression consisting of the designations of the elements of this aster, separated by a comma and united by parentheses. For example, (Earth, Moon) is the formula of an astr consisting of the Earth and the Moon.

Tired light is the phenomenon of cosmological attenuation of light and the phenomenon of cosmological expansion of light. The phenomenon of cosmological expansion of light manifests as cosmological redshift. Cosmological redshift is caused by an increase in the distance between ether spirals of light packets due to a decrease in the frequency of transit and synthesizing interactions of light etherons with external etherons in interstellar space and intergalactic space. Cosmological attenuation of light is caused by the decay of ether spirals of light packets due to a decrease in the frequency of transit and synthesizing interactions of light etherons with external etherons in interstellar space and intergalactic space.

Cosmic microwave background radiation is caused by the decay of protons in interstellar space and intergalactic space.

The rotation curve of a disk galaxy is determined by the fact that the repulsive ability of the ether field of an ether hyperobject decreases with increasing distance to the ether substance of this ether hyperobject, and the attractive ability of the ether field of an ether hyperobject increases with increasing distance to the ether substance of this ether hyperobject, as well as by the fact that the repulsive ability of the ether medium decreases with decreasing distance to the ether substance of an ether hyperobject, and the attractive ability of the ether medium increases with decreasing distance to the ether substance of an ether hyperobject.

The model of levels of matter in the Ether Theory of Matter is called the "Ether Standard Model of Matter". In the English version, the abbreviation for "Ether Standard Model of Matter" is "ÆSMoM".

This concludes the brief summary of the Ether Theory of Matter.

Next is a brief summary of the Ether Theory of Consciousness.

The Ether Theory of Consciousness is built on the concept of "Ether Neural Network".

In the English version, the abbreviation for "Ether Neural Network" is "ÆNN".

Ether neural networks are considered by the "Ether Neural Network Theory". In the English version, the abbreviation for "Ether Neural Network Theory" is "ÆNNT".

The information-technological name for "Ether Neural Network" is "Associative Broadcast Neural Network". In the English version, the abbreviation for "Associative Broadcast Neural Network" is "ABNN".

Information is patterns and associations between patterns.

Intelligence is the ability of neural networks to carry out the evolution of information for the purpose of evolution of matter.

The concept of ether neural network stems from the idea that each neuron of a natural neural network has an output broadcast electric pattern in the electrically conductive network between neurons, which can be selectively recognized by some other neurons of the neural network with which this neuron may not have direct synaptic contact.

A neuron during its axonal spike can transmit its output broadcast electric pattern into the electrically conductive network around neurons through the dendrites of other neurons that synaptically contact the axon of this neuron. Although the main mechanism in axodendritic synapses is chemical transmission through neurotransmitters, the fact of the spike in the axon is accompanied by transmembrane currents that create local changes in electric potential in the extracellular environment.

Dendrites not only receive signals through receptors but are themselves conductive cables with membrane potential that can be modulated by external electric currents. External electric currents propagate not only in the intercellular fluid but also along the dendrite membrane. The spatial configuration of a neuron's dendrites allows the neuron to confidently recognize a certain set of broadcast output electric patterns from other neurons.

This concludes the brief summary of the Ether Theory of Consciousness.

Next is a brief summary of the Ether Theory of Society.

The Ether Theory of Society is built on the concept of ether society.

Ether society is a materialistic society based on the philosophy of evolutionary ether materialism.

The concept of ether society stems from the idea that the inexhaustibility of hyperatomic energy obtained in hyperatomic reactors and the superiority of the global universal artificial intelligence of the socialized global artificial neural network will accelerate evolutionary social processes and ensure the overcoming of all fundamental social contradictions.

At its core, man is a group predatory animal with natural limitations of time, energy, memory, knowledge, intelligence and spirituality.

The natural limitations of man in the conditions of private ownership of matter, energy, knowledge, intelligence and management give rise to fundamental social contradictions.

Overcoming fundamental social contradictions is possible only if knowledge, matter, energy, intelligence, and management are socialized.

Socialized knowledge includes the theory of matter, theory of life, theory of consciousness, theory of society, as well as all other socially significant knowledge.

Socialized matter includes land, subsoil, infrastructure, people's enterprises, as well as all other socially significant material objects.

Socialized energy includes all energy obtained for social purposes at hyperatomic power plants and at power plants with other types of energy installations.

Socialized intelligence includes the entire intellectual process in the socialized global ether neural hypernetwork intended for purposes of social development.

Socialized management includes people's democracy, people's organizations, people's control, as well as all other socially significant elements of society management.

Ether science within the framework of artificial evolution of living beings will provide the possibility of creating genetically compiled humans with protection against genetic errors in cell division and functioning of the body. Artificial evolution of humans will eliminate the limitations of natural evolution.

The social system in which fundamental social contradictions are overcome by the intellectual evolutionary materialistic path is called evolutionary ether communism.

This concludes the brief summary of the Ether Theory of Society.

The above is a brief summary of the Ether Theory of Everything for dialogues with AI systems.