# Simulation Requirement
## NOTICE

1. All the files you submit must have your student ID at the front (112063702\_xxx.in/.pdf).
2. It's important to organize your project in the form of ' report ' rather than just answering the question.
3. If you just directly copy and paste the code from the lecture materials, you may encounter some character conversion issues. Please try writing the code yourself.
4. Just do your best. If you repeatedly try but are still unable to meet the requirements, documenting your attempts will still earn you partial credit.
5. Any act of cheating will be severely punished.

## WORKING SEQUENCE

1. Enter the workstation through MobaXterm.
2. Try running the program provided in the lecture materials. If it does not work, you can try executing the example code in ' File/Examples ' to find the problem.
3. Based on the knowledge learned in the lessons, adjust the key parameters until the specifications are met.
4. Look at the ' Victory Visual ' part in the handout, you may figure out how to visualize your answer.

## MNI PROJECT#1

## FEOL STI CMOS process

In this mini project, by using the FEOL CMOS process provided from slide 63 to 81 as your starting template, please modify the template to meet the following specifications.

<!-- image -->

1. Pad OX /SiN depo
2. AA (Active Area) Photo
3. STI etch (Shallow Trench Isolation)
4. HDP depo (STI depo)
5. STI CMP / clean
6. Well define and drive-in
7. Vt adjust implant
8. Gate OX define (Core and I/O)
9. Poly depo / poly etch
10. LDD implant
11. 11.S Spacer
12. S/D implant

## REQUIREMENT

## Specifications:

- (1) Effective channel length = 0.18 μm (Junction length, not Lg)
- (2) Spacer length = 0.13 μm
- (3) Gate oxide thickness = 5±2 nm

## Plot FEOL CMOS process .str files of the following process steps

1. STI process
2. Well define and drive in
3. Vt adjust implant
4. Poly define
5. LDD implant.
6. Spacer process
7. Source/Drain implant

## Upload your .in file along with your report (.pdf) to eeclass.

Note that the template used here is FEOL CMOS process, please follow and modify the corresponding command of the template step by step to complete your mini project.

## MINI PROJECT#2 MOSFET characteristics

In this mini project, by using the Metal-Oxide-Semiconductor Field-Effect Transistors (MOSFETs) provided from slide 83 to 96 as your starting template, please modify the template to meet the following specifications.

<!-- image -->

## NMOSFET

<!-- image -->

## PMOSFET

## MOSFETs structure

MOSFETs design Space

<!-- image -->

## REQUIREMENT

## Specifications:

- Adequate threshold voltage = 0.5 ± 0.1 V

```
(1) Channel length = 0.18 μm (2) Gate oxide thickness = 2±1 nm (3)
```

## Characteristics analysis:

1. Generate the 0.18 μ m device mesh for N-MOSFETs and P-MOSFETs. (as Figure 1)
2. Plot Id-Vg at Vds=0.05, 1V for N-MOSFETs and -Vds for  P-MOSFETs. (as Figure 2)
3. Plot Id-Vd at Vgs=0.4, 0.6, 0.8, 1V for N-MOSFETs and P-MOSFETs (with -Vgs, as Figure 3) .
4. Shows the threshold voltage (Vt) and subthreshold swing (SS) of your devices at Vds, n= 0.05, 1 V and Vds, p= -0.05, -1 V (as Figure4)
5. Plot Id-Vg at Vds, n= 0.05 (,p = -0.05) and Vgs=-3 to 3V for NMOSFETs and PMOSFETs C-V Characteristics (as Figure 5)
6. Please make a cutline at y=0.001 position and plot energy band-diagram at (Vd,Vg)= (0,0) and (1,1) as Figure 6.
7. Upload all .in file. (It ' s ok to merge or separate the code.)

## Samples (here only N-MOSFET)

<!-- image -->

Position (μm)

Figure 1 Device plot

<!-- image -->

## FIGURE 2 IDVG curve

FIGURE 3 IDVD curve

<!-- image -->

FIGURE 4 Please including two Vg

<!-- image -->

<!-- image -->

Gate Int. Vnltaee (V)

FIGURE 5 CV curve

FIGURE 6 Band diagram

<!-- image -->