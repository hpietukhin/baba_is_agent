% One encoding. Three layers.
%
%   base       geometry and the catalogues
%   meta(t)    sentences on the board, and the properties they give
%   step(t)    one action, and where objects sit before teleport
%   you(t)     YOU starts the shift
%   push(t)    PUSH joins the chain; text is always pushable
%   stop(t)    STOP blocks, and so does a wall while WALL IS STOP
%   melt(t)    HOT destroys MELT on the same cell
%   tele(t)    TELE swaps what stands on one teleporter onto the other
%   defeat(t)  DEFEAT after the swap
%   check(t)   is this a win?
%
% Python grounds meta(0), then every turn program at t = 1, 2, ...
% A property program stays grounded on turns where the sentence is
% broken: meta(t) simply derives nothing, and the effect does not fire.
% Push and stop read the sentences from before the move. Win, defeat,
% melt and teleport read the board after the move.
%
% below(Lower, Upper), as in the Sokoban encoding.
% The instance supplies location/1, leftOf/2, below/2, kind/2, word/2,
% and at/3 at time 0. Text that never moves is fixed_at/2 instead.
% dir(wait) is optional. wall/1, rock/1, flag/1 and water0/1 are the
% cells of a level whose walls and rocks are not objects.

#program base.

dir(left; right; up; down).
noun(baba; wall; rock; flag; love; water).
prop(you; stop; push; win; tele; hot; melt; defeat).

step(right, L, M) :- leftOf(L, M).
step(left, L, M) :- leftOf(M, L).
step(up, L, M) :- below(L, M).
step(down, L, M) :- below(M, L).
can_step(L, D) :- step(D, L, _).

% A level that does not use one of these still mentions it in a body.
fixed_at(missing, missing) :- #false.
flag(missing) :- #false.
wall(missing) :- #false.
rock(missing) :- #false.
water0(missing) :- #false.

#program meta(t).

coord(E, L, t) :- at(E, L, t).
coord(E, L, t) :- fixed_at(E, L).

formed(Noun, Prop, t) :-
    word(S, Noun), noun(Noun),
    word(I, is),
    word(P, Prop), prop(Prop),
    coord(S, Ls, t), coord(I, Li, t), coord(P, Lp, t),
    leftOf(Ls, Li), leftOf(Li, Lp).

formed(Noun, Prop, t) :-
    word(S, Noun), noun(Noun),
    word(I, is),
    word(P, Prop), prop(Prop),
    coord(S, Ls, t), coord(I, Li, t), coord(P, Lp, t),
    below(Li, Ls), below(Lp, Li).

formed(Noun, Extra, t) :-
    word(S, Noun), noun(Noun),
    word(I, is),
    word(P, Prop), prop(Prop),
    word(A, and),
    word(E, Extra), prop(Extra),
    coord(S, Ls, t), coord(I, Li, t), coord(P, Lp, t),
    coord(A, La, t), coord(E, Le, t),
    leftOf(Ls, Li), leftOf(Li, Lp), leftOf(Lp, La), leftOf(La, Le).

formed(Noun, Extra, t) :-
    word(S, Noun), noun(Noun),
    word(I, is),
    word(P, Prop), prop(Prop),
    word(A, and),
    word(E, Extra), prop(Extra),
    coord(S, Ls, t), coord(I, Li, t), coord(P, Lp, t),
    coord(A, La, t), coord(E, Le, t),
    below(Li, Ls), below(Lp, Li), below(La, Lp), below(Le, La).

you(E, t) :- kind(E, K), formed(K, you, t).
stop(E, t) :- kind(E, K), formed(K, stop, t).
win(E, t) :- kind(E, K), formed(K, win, t).
pushable(E, t) :- kind(E, K), formed(K, push, t).
pushable(E, t) :- word(E, _).
hot(E, t) :- kind(E, K), formed(K, hot, t).
teleport(E, t) :- kind(E, K), formed(K, tele, t).

won(t) :-
    you(A, t), win(B, t),
    at(A, L, t), at(B, L, t),
    A != B.
won(t) :-
    you(A, t), at(A, L, t), flag(L), formed(flag, win, t).

:- at(E, L1, t), at(E, L2, t), L1 != L2.

#program step(t).

1 { do(D, t) : dir(D) } 1.

moves(E, D, t) :- shifts(E, D, t), not chain_blocked(E, D, t).
changed(t) :- moves(E, D, t).
:- do(D, t), not changed(t).

displaced(E, t) :- moves(E, D, t).
% A direction that shifts nothing is the same step as wait.
:- do(D, t), dir(wait), D != wait, not displaced(E, t) : fluent(E).
moved(E, M, t) :-
    moves(E, D, t),
    at(E, L, t - 1),
    step(D, L, M).
moved(E, L, t) :- at(E, L, t - 1), not displaced(E, t).

#program you(t).

shifts(E, D, t) :- do(D, t), you(E, t - 1), D != wait.

#program push(t).

shifts(E, D, t) :-
    shifts(P, D, t),
    at(P, Lp, t - 1),
    step(D, Lp, L),
    at(E, L, t - 1),
    pushable(E, t - 1),
    not stop(E, t - 1),
    E != P.

#program stop(t).

blocked(E, D, t) :-
    shifts(E, D, t),
    at(E, L, t - 1),
    not can_step(L, D).
blocked(E, D, t) :-
    shifts(E, D, t),
    at(E, L, t - 1),
    step(D, L, M),
    at(O, M, t - 1),
    stop(O, t - 1).
blocked(E, D, t) :-
    shifts(E, D, t),
    at(E, L, t - 1),
    step(D, L, M),
    wall(M),
    formed(wall, stop, t - 1).
blocked(E, D, t) :-
    shifts(E, D, t),
    at(E, L, t - 1),
    step(D, L, M),
    fixed_at(T, M).

chain_blocked(E, D, t) :- blocked(E, D, t).
chain_blocked(E, D, t) :-
    shifts(E, D, t),
    at(E, L, t - 1),
    step(D, L, M),
    at(O, M, t - 1),
    shifts(O, D, t),
    chain_blocked(O, D, t).

#program melt(t).

melted(L, t) :-
    hot(H, t - 1),
    formed(water, melt, t - 1),
    moved(H, L, t),
    water0(L),
    not gone(L, t - 1).
gone(L, t) :- melted(L, t).
gone(L, t) :- gone(L, t - 1), water0(L), t > 1.
changed(t) :- melted(L, t).

#program tele(t).

apart(t) :-
    teleport(H1, t - 1), teleport(H2, t - 1),
    moved(H1, L1, t), moved(H2, L2, t),
    H1 != H2, L1 != L2.
teleported(E, t) :-
    apart(t),
    moved(E, L, t),
    moved(H, L, t),
    teleport(H, t - 1),
    E != H,
    not teleport(E, t - 1).
at(E, L2, t) :-
    teleported(E, t),
    moved(E, L, t),
    moved(H, L, t),
    teleport(H, t - 1),
    moved(H2, L2, t),
    teleport(H2, t - 1),
    H != H2.
at(E, L, t) :- moved(E, L, t), not teleported(E, t).
changed(t) :- teleported(E, t).

#program defeat(t).

:- you(A, t), at(A, L, t), rock(L), formed(rock, defeat, t).
:- you(A, t), at(A, L, t), water0(L), not gone(L, t), formed(water, defeat, t).

#program check(t).

#external query(t).
:- query(t), not won(t).

% Two steps that put every object back, and melt nothing, are a loop.
state_changed(t) :-
    t > 1, fluent(E), at(E, L, t), not at(E, L, t - 2).
melted_now(t) :- melted(L, t).
:- t > 1, not state_changed(t), not melted_now(t), not melted_now(t - 1).
