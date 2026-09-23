% ====================================================================
% Baba Is You — ASP Physics Model (MVP)
% Static rules only (from ruleIs facts). No text block dynamics.
% ====================================================================

% --- Horizon ----------------------------------------------------------
max_horizon(10).

% --- Time (recursive generation) -------------------------------------
time(0).
time(T+1) :- time(T), max_horizon(H), T < H.

% --- Actions ---------------------------------------------------------
action(up). action(down). action(left). action(right). action(idle).
1 { do(A,T) : action(A) } 1 :- time(T).

% --- Initial positions (from AtInit facts) --------------------------
holds(at(ID,O,X,Y),0) :- atInit(ID,O,X,Y).

% --- Inertia ---------------------------------------------------------
holds(at(ID,O,X,Y),T) :-
    holds(at(ID,O,X,Y),T-1),
    not moved(ID,T-1),
    time(T).

% --- Property derivation (static from ruleIs) ------------------------
holds(property(O,P),T) :-
    ruleIs(O,P),
    holds(at(_,O,_,_),T),
    time(T).

% --- Movement vectors -----------------------------------------------
dx(right,1). dx(left,-1). dx(up,0). dx(down,0).
dy(right,0). dy(left,0). dy(down,1). dy(up,-1).

% YOU objects move in the chosen direction
moving(ID,DX,DY,T) :-
    do(D,T),
    holds(at(ID,O,X,Y),T),
    holds(property(O,you),T),
    dx(D,DX), dy(D,DY).

% PUSH objects move when a moving object enters their cell
moving(IDP,DX,DY,T) :-
    moving(ID,DX,DY,T),
    holds(at(ID,_,NX,NY),T),
    holds(at(IDP,O2,NX,NY),T),
    holds(property(O2,push),T),
    IDP != ID.

% --- Integrity constraints -------------------------------------------

% Cannot move into a STOP object
:- moving(ID,DX,DY,T),
   holds(at(ID,_,X,Y),T),
   NX = X + DX, NY = Y + DY,
   holds(at(_,O2,NX,NY),T),
   holds(property(O2,stop),T).

% PUSH target cannot move into STOP
:- moving(ID,DX,DY,T),
   moving(IDP,DX,DY,T),
   holds(at(ID,_,X,Y),T),
   holds(at(ID,_,NX,NY),T),
   holds(at(IDP,_,NX,NY),T),
   NX2 = NX + DX, NY2 = NY + DY,
   holds(at(_,O3,NX2,NY2),T),
   holds(property(O3,stop),T),
   IDP != ID.

% PUSH target cannot push into a non-moving PUSH object
:- moving(ID,DX,DY,T),
   moving(IDP,DX,DY,T),
   holds(at(ID,_,X,Y),T),
   holds(at(ID,_,NX,NY),T),
   holds(at(IDP,_,NX,NY),T),
   NX2 = NX + DX, NY2 = NY + DY,
   holds(at(IDO,O4,NX2,NY2),T),
   not moving(IDO,DX,DY,T),
   holds(property(O4,push),T),
   IDP != ID.

% --- Apply movement --------------------------------------------------
moved(ID,T) :- moving(ID,_,_,T).

holds(at(ID,O,NX,NY),T+1) :-
    moving(ID,DX,DY,T),
    holds(at(ID,O,X,Y),T),
    NX = X + DX, NY = Y + DY,
    time(T).

% --- WIN condition ---------------------------------------------------
winning(T) :-
    holds(at(_,O1,X,Y),T),
    holds(property(O1,you),T),
    holds(at(_,O2,X,Y),T),
    holds(property(O2,win),T),
    time(T).

won :- winning(T), time(T).

% Must reach a winning state
:- not won.

% --- Minimize total time steps --------------------------------------
#minimize { 1@2,T : do(A,T), A != idle }.
