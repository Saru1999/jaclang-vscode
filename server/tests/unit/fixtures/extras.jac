node extra_node;
edge extra_edge;
walker extra_walker {
    has anchor a;
    has private b;
    has c;
}

graph extra_graph {
    has anchor graph_root;

    spawn {
        graph_root = spawn node::extra_node;
    }
}

walker init {
    can date.
}