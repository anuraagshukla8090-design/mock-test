"""
Official chapter ordering and aliases for supported exams.

Structure:
    SYLLABUS_DATA = {
        (exam_name, subject): [
            {
                "chapter_name": "...",   # canonical NCERT name
                "chapter_aliases": [...] # common alternate names
            },
            ...
        ]
    }

chapter_order is 1-indexed and assigned by list position.
This data is inserted at migration time via op.bulk_insert().
It is NOT loaded at runtime — SyllabusResolver always queries the DB.
"""
from __future__ import annotations

SYLLABUS_DATA: dict[tuple[str, str], list[dict]] = {

    # ─────────────────────────────────────────────────────────────────────────
    # JEE Main — Physics  (NCERT Class 11 + 12, NTA 2024 syllabus)
    # ─────────────────────────────────────────────────────────────────────────
    ("JEE Main", "physics"): [
        {
            "chapter_name": "Physical World and Measurement",
            "chapter_aliases": ["Physical World", "Units and Measurement",
                                 "Units and Dimensions", "Measurement"],
        },
        {
            "chapter_name": "Kinematics",
            "chapter_aliases": ["Motion in a Straight Line",
                                 "Motion in a Plane", "Projectile Motion",
                                 "Relative Motion"],
        },
        {
            "chapter_name": "Laws of Motion",
            "chapter_aliases": ["Newton's Laws", "Newton's Laws of Motion",
                                 "NLM", "Friction"],
        },
        {
            "chapter_name": "Work, Energy and Power",
            "chapter_aliases": ["Work Energy Theorem", "Work and Energy",
                                 "Conservation of Energy"],
        },
        {
            "chapter_name": "Motion of System of Particles and Rigid Body",
            "chapter_aliases": ["Rotational Motion", "Rigid Body",
                                 "System of Particles", "Rotational Dynamics",
                                 "Moment of Inertia", "Angular Momentum",
                                 "Torque"],
        },
        {
            "chapter_name": "Gravitation",
            "chapter_aliases": ["Gravity", "Kepler's Laws",
                                 "Satellite Motion", "Orbital Mechanics"],
        },
        {
            "chapter_name": "Properties of Bulk Matter",
            "chapter_aliases": ["Mechanical Properties of Solids",
                                 "Mechanical Properties of Fluids",
                                 "Elasticity", "Viscosity", "Surface Tension",
                                 "Fluid Mechanics"],
        },
        {
            "chapter_name": "Thermodynamics",
            "chapter_aliases": ["Laws of Thermodynamics",
                                 "Thermal Physics", "Heat and Thermodynamics"],
        },
        {
            "chapter_name": "Kinetic Theory of Gases",
            "chapter_aliases": ["Kinetic Theory", "Ideal Gas", "KTG",
                                 "Thermal Properties of Matter"],
        },
        {
            "chapter_name": "Oscillations and Waves",
            "chapter_aliases": ["SHM", "Simple Harmonic Motion",
                                 "Wave Motion", "Sound Waves",
                                 "Oscillations", "Waves"],
        },
        {
            "chapter_name": "Electrostatics",
            "chapter_aliases": ["Electric Charges and Fields",
                                 "Electric Potential", "Capacitance",
                                 "Coulomb's Law", "Gauss Law"],
        },
        {
            "chapter_name": "Current Electricity",
            "chapter_aliases": ["Ohm's Law", "Kirchhoff's Laws",
                                 "Electric Circuits", "Wheatstone Bridge"],
        },
        {
            "chapter_name": "Magnetic Effects of Current and Magnetism",
            "chapter_aliases": ["Magnetism", "Magnetic Force",
                                 "Biot-Savart Law", "Ampere's Law",
                                 "Moving Charges and Magnetism"],
        },
        {
            "chapter_name": "Electromagnetic Induction and Alternating Currents",
            "chapter_aliases": ["EMI", "AC Circuits", "Electromagnetic Induction",
                                 "Faraday's Law", "Alternating Current",
                                 "Inductance", "Transformer"],
        },
        {
            "chapter_name": "Electromagnetic Waves",
            "chapter_aliases": ["EM Waves", "Maxwell's Equations",
                                 "Electromagnetic Spectrum"],
        },
        {
            "chapter_name": "Ray Optics and Optical Instruments",
            "chapter_aliases": ["Ray Optics", "Optics",
                                 "Reflection and Refraction",
                                 "Lenses and Mirrors", "Optical Instruments"],
        },
        {
            "chapter_name": "Wave Optics",
            "chapter_aliases": ["Interference", "Diffraction",
                                 "Polarisation", "Huygens Principle",
                                 "Young's Double Slit"],
        },
        {
            "chapter_name": "Dual Nature of Radiation and Matter",
            "chapter_aliases": ["Photoelectric Effect", "Dual Nature",
                                 "de Broglie Wavelength", "Matter Waves",
                                 "Quantum Physics"],
        },
        {
            "chapter_name": "Atoms and Nuclei",
            "chapter_aliases": ["Atomic Structure", "Nuclear Physics",
                                 "Radioactivity", "Nuclear Reactions",
                                 "Bohr Model"],
        },
        {
            "chapter_name": "Semiconductor Electronics",
            "chapter_aliases": ["Electronics", "Semiconductors",
                                 "Diodes and Transistors", "Logic Gates",
                                 "Electronic Devices"],
        },
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # JEE Main — Chemistry  (Class 11 + 12, NTA 2024 syllabus)
    # ─────────────────────────────────────────────────────────────────────────
    ("JEE Main", "chemistry"): [
        # Class 11
        {
            "chapter_name": "Some Basic Concepts of Chemistry",
            "chapter_aliases": ["Basic Chemistry", "Mole Concept",
                                 "Stoichiometry", "Atomic Mass"],
        },
        {
            "chapter_name": "Structure of Atom",
            "chapter_aliases": ["Atomic Structure", "Quantum Numbers",
                                 "Bohr Model", "Electronic Configuration"],
        },
        {
            "chapter_name": "Classification of Elements and Periodicity in Properties",
            "chapter_aliases": ["Periodic Table", "Periodic Properties",
                                 "Periodicity"],
        },
        {
            "chapter_name": "Chemical Bonding and Molecular Structure",
            "chapter_aliases": ["Chemical Bonding", "Molecular Structure",
                                 "VSEPR", "Hybridization", "Bond Order"],
        },
        {
            "chapter_name": "States of Matter",
            "chapter_aliases": ["Gaseous State", "Liquid State",
                                 "Gas Laws", "Real Gases"],
        },
        {
            "chapter_name": "Thermodynamics",
            "chapter_aliases": ["Chemical Thermodynamics",
                                 "Enthalpy", "Entropy", "Gibbs Energy",
                                 "Hess Law"],
        },
        {
            "chapter_name": "Equilibrium",
            "chapter_aliases": ["Chemical Equilibrium", "Ionic Equilibrium",
                                 "Le Chatelier's Principle", "Kp Kc",
                                 "pH", "Buffer Solutions"],
        },
        {
            "chapter_name": "Redox Reactions",
            "chapter_aliases": ["Oxidation Reduction", "Oxidation State",
                                 "Redox", "Balancing Redox Equations"],
        },
        {
            "chapter_name": "Hydrogen",
            "chapter_aliases": ["Hydrogen and its Compounds",
                                 "Water", "Hydrogen Peroxide"],
        },
        {
            "chapter_name": "The s-Block Elements",
            "chapter_aliases": ["s Block", "Alkali Metals",
                                 "Alkaline Earth Metals", "Group 1 Group 2"],
        },
        {
            "chapter_name": "The p-Block Elements (Group 13 and 14)",
            "chapter_aliases": ["p Block Class 11", "Boron Family",
                                 "Carbon Family", "Group 13", "Group 14"],
        },
        {
            "chapter_name": "Organic Chemistry: Some Basic Principles and Techniques",
            "chapter_aliases": ["Organic Chemistry Basics",
                                 "GOC", "General Organic Chemistry",
                                 "IUPAC Nomenclature", "Isomerism",
                                 "Reaction Mechanisms"],
        },
        {
            "chapter_name": "Hydrocarbons",
            "chapter_aliases": ["Alkanes", "Alkenes", "Alkynes",
                                 "Aromatic Hydrocarbons", "Benzene"],
        },
        {
            "chapter_name": "Environmental Chemistry",
            "chapter_aliases": ["Pollution", "Environmental Issues",
                                 "Green Chemistry"],
        },
        # Class 12
        {
            "chapter_name": "The Solid State",
            "chapter_aliases": ["Solid State", "Crystal Structure",
                                 "Unit Cell", "Defects in Solids"],
        },
        {
            "chapter_name": "Solutions",
            "chapter_aliases": ["Colligative Properties",
                                 "Vapour Pressure", "Osmosis",
                                 "Henry's Law", "Raoult's Law"],
        },
        {
            "chapter_name": "Electrochemistry",
            "chapter_aliases": ["Electrochemical Cells",
                                 "Nernst Equation", "Electrolysis",
                                 "Galvanic Cell", "Faraday's Laws"],
        },
        {
            "chapter_name": "Chemical Kinetics",
            "chapter_aliases": ["Rate of Reaction", "Rate Law",
                                 "Arrhenius Equation", "Order of Reaction"],
        },
        {
            "chapter_name": "Surface Chemistry",
            "chapter_aliases": ["Adsorption", "Catalysis",
                                 "Colloids", "Emulsions"],
        },
        {
            "chapter_name": "General Principles and Processes of Isolation of Elements",
            "chapter_aliases": ["Metallurgy", "Extraction of Metals",
                                 "Refining"],
        },
        {
            "chapter_name": "The p-Block Elements (Group 15 to 18)",
            "chapter_aliases": ["p Block Class 12", "Nitrogen Family",
                                 "Oxygen Family", "Halogen Family",
                                 "Noble Gases", "Group 15", "Group 16",
                                 "Group 17", "Group 18"],
        },
        {
            "chapter_name": "The d and f Block Elements",
            "chapter_aliases": ["d Block", "f Block",
                                 "Transition Elements",
                                 "Inner Transition Elements",
                                 "Lanthanides", "Actinides"],
        },
        {
            "chapter_name": "Coordination Compounds",
            "chapter_aliases": ["Complex Compounds",
                                 "Coordination Chemistry",
                                 "Werner Theory", "Ligands",
                                 "Crystal Field Theory"],
        },
        {
            "chapter_name": "Haloalkanes and Haloarenes",
            "chapter_aliases": ["Alkyl Halides", "Aryl Halides",
                                 "Nucleophilic Substitution",
                                 "SN1 SN2"],
        },
        {
            "chapter_name": "Alcohols, Phenols and Ethers",
            "chapter_aliases": ["Alcohol", "Phenol", "Ether",
                                 "Hydroxyl Compounds"],
        },
        {
            "chapter_name": "Aldehydes, Ketones and Carboxylic Acids",
            "chapter_aliases": ["Aldehyde", "Ketone",
                                 "Carboxylic Acid",
                                 "Carbonyl Compounds", "Aldol Condensation"],
        },
        {
            "chapter_name": "Amines",
            "chapter_aliases": ["Nitrogen Compounds", "Amine",
                                 "Diazonium Salts"],
        },
        {
            "chapter_name": "Biomolecules",
            "chapter_aliases": ["Carbohydrates", "Proteins",
                                 "Nucleic Acids", "Vitamins",
                                 "Enzymes", "Hormones"],
        },
        {
            "chapter_name": "Polymers",
            "chapter_aliases": ["Addition Polymers",
                                 "Condensation Polymers",
                                 "Natural Rubber", "Synthetic Polymers"],
        },
        {
            "chapter_name": "Chemistry in Everyday Life",
            "chapter_aliases": ["Drugs", "Cleansing Agents",
                                 "Food Chemistry"],
        },
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # JEE Main — Mathematics  (NTA 2024 syllabus)
    # ─────────────────────────────────────────────────────────────────────────
    ("JEE Main", "mathematics"): [
        {
            "chapter_name": "Sets, Relations and Functions",
            "chapter_aliases": ["Sets", "Relations", "Functions",
                                 "Types of Functions"],
        },
        {
            "chapter_name": "Complex Numbers and Quadratic Equations",
            "chapter_aliases": ["Complex Numbers", "Quadratic Equations",
                                 "Argand Plane", "De Moivre's Theorem"],
        },
        {
            "chapter_name": "Matrices and Determinants",
            "chapter_aliases": ["Matrices", "Determinants",
                                 "Matrix Algebra", "Inverse of Matrix"],
        },
        {
            "chapter_name": "Permutations and Combinations",
            "chapter_aliases": ["PnC", "Counting", "Combinatorics",
                                 "Permutation", "Combination"],
        },
        {
            "chapter_name": "Mathematical Induction",
            "chapter_aliases": ["Principle of Mathematical Induction",
                                 "PMI"],
        },
        {
            "chapter_name": "Binomial Theorem and its Simple Applications",
            "chapter_aliases": ["Binomial Theorem", "Binomial Expansion",
                                 "Pascal's Triangle"],
        },
        {
            "chapter_name": "Sequences and Series",
            "chapter_aliases": ["AP GP", "Arithmetic Progression",
                                 "Geometric Progression",
                                 "Arithmetic Mean", "Geometric Mean",
                                 "Sum of Series"],
        },
        {
            "chapter_name": "Limit, Continuity and Differentiability",
            "chapter_aliases": ["Limits", "Continuity",
                                 "Differentiability", "LCD",
                                 "Calculus Basics"],
        },
        {
            "chapter_name": "Integral Calculus",
            "chapter_aliases": ["Integration", "Definite Integral",
                                 "Indefinite Integral",
                                 "Area Under Curve"],
        },
        {
            "chapter_name": "Differential Equations",
            "chapter_aliases": ["ODE", "Ordinary Differential Equations",
                                 "Variable Separable"],
        },
        {
            "chapter_name": "Coordinate Geometry",
            "chapter_aliases": ["Straight Lines", "Circles",
                                 "Parabola", "Ellipse", "Hyperbola",
                                 "Conic Sections"],
        },
        {
            "chapter_name": "Three-Dimensional Geometry",
            "chapter_aliases": ["3D Geometry", "Direction Cosines",
                                 "Plane in 3D", "Line in 3D"],
        },
        {
            "chapter_name": "Vector Algebra",
            "chapter_aliases": ["Vectors", "Dot Product",
                                 "Cross Product", "Vector Triple Product"],
        },
        {
            "chapter_name": "Statistics and Probability",
            "chapter_aliases": ["Statistics", "Probability",
                                 "Mean Variance", "Bayes Theorem",
                                 "Conditional Probability"],
        },
        {
            "chapter_name": "Trigonometry",
            "chapter_aliases": ["Trigonometric Functions",
                                 "Inverse Trigonometry",
                                 "Trigonometric Identities",
                                 "Heights and Distances"],
        },
        {
            "chapter_name": "Mathematical Reasoning",
            "chapter_aliases": ["Logic", "Logical Reasoning",
                                 "Statements and Connectives"],
        },
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # NEET — Physics  (same chapters as JEE Main physics)
    # ─────────────────────────────────────────────────────────────────────────
    # Populated below by copying JEE Main physics rows

    # ─────────────────────────────────────────────────────────────────────────
    # NEET — Chemistry  (same chapters as JEE Main chemistry)
    # ─────────────────────────────────────────────────────────────────────────
    # Populated below by copying JEE Main chemistry rows

    # ─────────────────────────────────────────────────────────────────────────
    # NEET — Biology  (38 chapters — Botany + Zoology, NCERT Class 11 + 12)
    # ─────────────────────────────────────────────────────────────────────────
    ("NEET", "biology"): [
        # Class 11 — Botany
        {
            "chapter_name": "The Living World",
            "chapter_aliases": ["Introduction to Biology", "Diversity of Life"],
        },
        {
            "chapter_name": "Biological Classification",
            "chapter_aliases": ["Classification", "Five Kingdom Classification",
                                 "Taxonomy"],
        },
        {
            "chapter_name": "Plant Kingdom",
            "chapter_aliases": ["Kingdom Plantae", "Algae Bryophyta",
                                 "Pteridophyta", "Gymnosperms", "Angiosperms"],
        },
        {
            "chapter_name": "Animal Kingdom",
            "chapter_aliases": ["Kingdom Animalia", "Classification of Animals",
                                 "Phyla"],
        },
        {
            "chapter_name": "Morphology of Flowering Plants",
            "chapter_aliases": ["Flowering Plants Morphology",
                                 "Root Stem Leaf", "Inflorescence",
                                 "Flower Fruit Seed"],
        },
        {
            "chapter_name": "Anatomy of Flowering Plants",
            "chapter_aliases": ["Plant Anatomy", "Plant Tissues",
                                 "Meristematic Tissue", "Permanent Tissue"],
        },
        {
            "chapter_name": "Structural Organisation in Animals",
            "chapter_aliases": ["Animal Tissues", "Epithelial Tissue",
                                 "Connective Tissue", "Nervous Tissue",
                                 "Muscular Tissue", "Earthworm Cockroach Frog"],
        },
        {
            "chapter_name": "Cell: The Unit of Life",
            "chapter_aliases": ["Cell Biology", "Cell Structure",
                                 "Prokaryotic Cell", "Eukaryotic Cell",
                                 "Cell Organelles"],
        },
        {
            "chapter_name": "Biomolecules",
            "chapter_aliases": ["Carbohydrates", "Proteins", "Lipids",
                                 "Nucleic Acids", "Enzymes",
                                 "Macromolecules"],
        },
        {
            "chapter_name": "Cell Cycle and Cell Division",
            "chapter_aliases": ["Mitosis", "Meiosis", "Cell Division",
                                 "Cell Cycle"],
        },
        # Class 11 — Botany (Plant Physiology)
        {
            "chapter_name": "Transport in Plants",
            "chapter_aliases": ["Osmosis", "Diffusion",
                                 "Translocation in Phloem",
                                 "Water Potential"],
        },
        {
            "chapter_name": "Mineral Nutrition",
            "chapter_aliases": ["Mineral Absorption", "Essential Elements",
                                 "Nitrogen Fixation"],
        },
        {
            "chapter_name": "Photosynthesis in Higher Plants",
            "chapter_aliases": ["Photosynthesis", "Light Reactions",
                                 "Calvin Cycle", "C3 C4 Plants",
                                 "Chloroplast"],
        },
        {
            "chapter_name": "Respiration in Plants",
            "chapter_aliases": ["Plant Respiration", "Glycolysis",
                                 "Krebs Cycle", "Oxidative Phosphorylation",
                                 "Fermentation"],
        },
        {
            "chapter_name": "Plant Growth and Development",
            "chapter_aliases": ["Plant Hormones", "Phytohormones",
                                 "Auxin Gibberellin Cytokinin",
                                 "Photoperiodism", "Vernalisation"],
        },
        # Class 11 — Zoology (Human Physiology)
        {
            "chapter_name": "Digestion and Absorption",
            "chapter_aliases": ["Digestive System", "Human Digestion",
                                 "GI Tract", "Gut"],
        },
        {
            "chapter_name": "Breathing and Exchange of Gases",
            "chapter_aliases": ["Respiratory System", "Lungs",
                                 "Gas Exchange", "Breathing"],
        },
        {
            "chapter_name": "Body Fluids and Circulation",
            "chapter_aliases": ["Circulatory System", "Heart",
                                 "Blood", "Lymph", "Blood Groups",
                                 "Cardiac Cycle"],
        },
        {
            "chapter_name": "Excretory Products and their Elimination",
            "chapter_aliases": ["Excretion", "Kidney", "Nephron",
                                 "Urine Formation", "Dialysis"],
        },
        {
            "chapter_name": "Locomotion and Movement",
            "chapter_aliases": ["Muscular System", "Skeletal System",
                                 "Muscle Contraction", "Joints"],
        },
        {
            "chapter_name": "Neural Control and Coordination",
            "chapter_aliases": ["Nervous System", "Neuron",
                                 "Brain", "Spinal Cord",
                                 "Action Potential", "Synapse"],
        },
        {
            "chapter_name": "Chemical Coordination and Integration",
            "chapter_aliases": ["Endocrine System", "Hormones",
                                 "Pituitary", "Thyroid",
                                 "Insulin", "Adrenal"],
        },
        # Class 12 — Botany (Reproduction)
        {
            "chapter_name": "Reproduction in Organisms",
            "chapter_aliases": ["Asexual Reproduction",
                                 "Sexual Reproduction",
                                 "Modes of Reproduction"],
        },
        {
            "chapter_name": "Sexual Reproduction in Flowering Plants",
            "chapter_aliases": ["Pollination", "Fertilisation in Plants",
                                 "Double Fertilisation",
                                 "Embryo Development", "Seed Formation"],
        },
        # Class 12 — Zoology (Reproduction)
        {
            "chapter_name": "Human Reproduction",
            "chapter_aliases": ["Male Reproductive System",
                                 "Female Reproductive System",
                                 "Gametogenesis", "Fertilisation",
                                 "Pregnancy", "Parturition"],
        },
        {
            "chapter_name": "Reproductive Health",
            "chapter_aliases": ["STDs", "Contraception",
                                 "Assisted Reproductive Technology",
                                 "IVF"],
        },
        # Class 12 — Genetics and Evolution
        {
            "chapter_name": "Principles of Inheritance and Variation",
            "chapter_aliases": ["Mendelian Genetics", "Mendel's Laws",
                                 "Heredity", "Chromosomal Theory",
                                 "Linkage", "Crossing Over"],
        },
        {
            "chapter_name": "Molecular Basis of Inheritance",
            "chapter_aliases": ["DNA Structure", "DNA Replication",
                                 "Transcription", "Translation",
                                 "Gene Expression", "Genetic Code",
                                 "Central Dogma"],
        },
        {
            "chapter_name": "Evolution",
            "chapter_aliases": ["Darwin's Theory", "Natural Selection",
                                 "Origin of Life", "Human Evolution",
                                 "Hardy Weinberg"],
        },
        # Class 12 — Biology in Human Welfare
        {
            "chapter_name": "Human Health and Disease",
            "chapter_aliases": ["Immunity", "Diseases", "Pathogens",
                                 "Cancer", "Drugs and Alcohol",
                                 "AIDS", "Vaccination"],
        },
        {
            "chapter_name": "Strategies for Enhancement in Food Production",
            "chapter_aliases": ["Animal Husbandry", "Plant Breeding",
                                 "Biofortification",
                                 "Single Cell Protein"],
        },
        {
            "chapter_name": "Microbes in Human Welfare",
            "chapter_aliases": ["Useful Microbes", "Fermentation",
                                 "Biogas", "Sewage Treatment",
                                 "Antibiotics"],
        },
        # Class 12 — Biotechnology
        {
            "chapter_name": "Biotechnology: Principles and Processes",
            "chapter_aliases": ["Biotechnology Principles",
                                 "Recombinant DNA Technology",
                                 "Genetic Engineering",
                                 "PCR", "Restriction Enzymes",
                                 "Gel Electrophoresis"],
        },
        {
            "chapter_name": "Biotechnology and its Applications",
            "chapter_aliases": ["Biotechnology Applications",
                                 "GM Crops", "Transgenic Animals",
                                 "Insulin Production",
                                 "Gene Therapy"],
        },
        # Class 12 — Ecology
        {
            "chapter_name": "Organisms and Populations",
            "chapter_aliases": ["Population Ecology",
                                 "Population Attributes",
                                 "Growth Models", "Interspecific Interactions"],
        },
        {
            "chapter_name": "Ecosystem",
            "chapter_aliases": ["Ecosystem Structure",
                                 "Energy Flow", "Food Chain",
                                 "Nutrient Cycling",
                                 "Ecological Pyramids"],
        },
        {
            "chapter_name": "Biodiversity and Conservation",
            "chapter_aliases": ["Biodiversity", "Species Diversity",
                                 "Hotspots", "Conservation",
                                 "Endangered Species", "In Situ Ex Situ"],
        },
        {
            "chapter_name": "Environmental Issues",
            "chapter_aliases": ["Pollution", "Global Warming",
                                 "Greenhouse Effect",
                                 "Ozone Depletion",
                                 "Deforestation"],
        },
    ],
}

# NEET Physics and Chemistry share the same chapters as JEE Main
SYLLABUS_DATA[("NEET", "physics")] = SYLLABUS_DATA[("JEE Main", "physics")]
SYLLABUS_DATA[("NEET", "chemistry")] = SYLLABUS_DATA[("JEE Main", "chemistry")]


def get_seed_rows() -> list[dict]:
    """
    Returns flat list of dicts suitable for alembic op.bulk_insert().
    chapter_order is 1-indexed per (exam_name, subject) partition.
    """
    import uuid
    rows = []
    for (exam_name, subject), chapters in SYLLABUS_DATA.items():
        for idx, chapter in enumerate(chapters, start=1):
            rows.append({
                "id": str(uuid.uuid4()),
                "exam_name": exam_name,
                "subject": subject,
                "chapter_name": chapter["chapter_name"],
                "chapter_order": idx,
                "chapter_aliases": chapter["chapter_aliases"],
            })
    return rows
